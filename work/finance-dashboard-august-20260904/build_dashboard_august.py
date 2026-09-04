#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
WORK = BASE / 'work/finance-dashboard-august-20260904'
SHEET_ID = '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
HELPER = BASE / 'scripts/mgs_google_workspace_auth.py'
BACKUP_PATH = WORK / 'dashboard-august-prebuild-backup.json'
CANDIDATE_PATH = WORK / 'dashboard-august-build-candidate.json'

spec = importlib.util.spec_from_file_location('mgs_google_workspace_auth', HELPER)
if not spec or not spec.loader:
    raise RuntimeError('canonical Google helper unavailable')
google = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = google
spec.loader.exec_module(google)
token = google.service_account_access_token([google.DRIVE_SCOPE, google.SHEETS_SCOPE])
project = google.service_account_project_id()
sa = google.load_service_account()
if sa.get('client_email') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com' or project != 'mgs-core-prod':
    raise RuntimeError('canonical Google identity mismatch')


def api(method: str, url: str, payload=None):
    status, data = google.api_json(method, url, token, payload, quota_project=project)
    if status != 200:
        err = (data.get('error') or {}).get('status') or f'HTTP_{status}'
        msg = (data.get('error') or {}).get('message') or ''
        raise RuntimeError(f'Google API failure: {err}: {msg[:160]}')
    return status, data


def metadata_get(fields='spreadsheetId,properties,sheets(properties,charts,basicFilter)', include_grid=False, ranges=None):
    params = [('includeGridData', 'true' if include_grid else 'false'), ('fields', fields)]
    for r in ranges or []:
        params.append(('ranges', r))
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?' + urllib.parse.urlencode(params)
    return api('GET', url)[1]


def values_get(a1: str, render: str):
    encoded = urllib.parse.quote(a1, safe='')
    _, data = api('GET', (
        f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}'
        f'?majorDimension=ROWS&valueRenderOption={render}'
    ))
    return data.get('values') or []


def formula_hash(grid) -> str:
    raw = json.dumps(grid, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def cell(grid, row: int, col: int):
    if row < 1 or col < 1 or row > len(grid):
        return ''
    values = grid[row - 1]
    return values[col - 1] if col <= len(values) else ''


def close(a, b, tol=1e-7):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def write_json(path: Path, obj):
    raw = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    path.write_text(raw, encoding='utf-8')
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def batch_update(requests):
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests': requests})[1]


def rgb(hex_value: str):
    h = hex_value.lstrip('#')
    return {'red': int(h[0:2],16)/255, 'green': int(h[2:4],16)/255, 'blue': int(h[4:6],16)/255}


def grid(sheet_id, sr, er, sc, ec):
    return {'sheetId': sheet_id, 'startRowIndex': sr, 'endRowIndex': er, 'startColumnIndex': sc, 'endColumnIndex': ec}


def series_range(sheet_id, sr, er, sc, ec):
    return {'sourceRange': {'sources': [grid(sheet_id, sr, er, sc, ec)]}}

backup = json.loads(BACKUP_PATH.read_text(encoding='utf-8'))
candidate = json.loads(CANDIDATE_PATH.read_text(encoding='utf-8'))
if candidate['target_tabs'] != ['BASE_DASH', 'DASH EXECUTIVO']:
    raise RuntimeError('candidate target tabs mismatch')

created_ids = []
canary_title = f'__MGS_DASH_CANARY_{int(time.time())}'
canary_deleted = False
try:
    # Freeze against any manual or concurrent change since the backup.
    current_meta = metadata_get('spreadsheetId,properties,sheets.properties')
    current_titles = [s['properties']['title'] for s in current_meta.get('sheets') or []]
    if set(candidate['target_tabs']).intersection(current_titles):
        raise RuntimeError('target dashboard tab appeared after preflight')
    source_formula = values_get("'Agosto 2026'!A1:APE338", 'FORMULA')
    caixa_formula = values_get("'CAIXA SINTETICO'!A1:R85", 'FORMULA')
    if formula_hash(source_formula) != candidate['source_formula_hashes']['Agosto 2026']:
        raise RuntimeError('Agosto 2026 changed after preflight')
    if formula_hash(caixa_formula) != candidate['source_formula_hashes']['CAIXA SINTETICO']:
        raise RuntimeError('CAIXA SINTETICO changed after preflight')

    # Structural canary: add one temporary tab, read it back, then delete it.
    canary_reply = batch_update([{'addSheet': {'properties': {'title': canary_title, 'gridProperties': {'rowCount': 10, 'columnCount': 5}}}}])
    canary_id = canary_reply['replies'][0]['addSheet']['properties']['sheetId']
    meta_after_canary = metadata_get('sheets.properties')
    if not any(s['properties']['title'] == canary_title and s['properties']['sheetId'] == canary_id for s in meta_after_canary.get('sheets') or []):
        raise RuntimeError('structural canary add readback failed')
    batch_update([{'deleteSheet': {'sheetId': canary_id}}])
    canary_deleted = True
    if any(s['properties']['title'] == canary_title for s in metadata_get('sheets.properties').get('sheets') or []):
        raise RuntimeError('structural canary delete readback failed')

    # Create the two final tabs only after the canary fully disappears.
    create_reply = batch_update([
        {'addSheet': {'properties': {'title': 'BASE_DASH', 'tabColor': rgb('#64748B'), 'gridProperties': {'rowCount': 500, 'columnCount': 22, 'frozenRowCount': 1}}}},
        {'addSheet': {'properties': {'title': 'DASH EXECUTIVO', 'tabColor': rgb('#2563EB'), 'gridProperties': {'rowCount': 120, 'columnCount': 13, 'hideGridlines': True}}}},
    ])
    base_id = create_reply['replies'][0]['addSheet']['properties']['sheetId']
    dash_id = create_reply['replies'][1]['addSheet']['properties']['sheetId']
    created_ids = [base_id, dash_id]

    # Write normalized base plus sparse dashboard formulas/labels.
    value_data = [{
        'range': f"'BASE_DASH'!A1:V{candidate['base_row_count']}",
        'majorDimension': 'ROWS',
        'values': candidate['base_rows'],
    }]
    for a1, values in candidate['dashboard_values'].items():
        value_data.append({'range': f"'DASH EXECUTIVO'!{a1}", 'majorDimension': 'ROWS', 'values': values})
    _, write_result = api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate', {
        'valueInputOption': 'USER_ENTERED',
        'data': value_data,
        'includeValuesInResponse': False,
    })
    if write_result.get('totalUpdatedCells', 0) < candidate['base_row_count'] * 20:
        raise RuntimeError(f"unexpectedly low dashboard write count: {write_result.get('totalUpdatedCells')}")

    dark = rgb('#0F172A'); blue = rgb('#2563EB'); light_blue = rgb('#DBEAFE')
    white = rgb('#FFFFFF'); slate = rgb('#334155'); light = rgb('#F8FAFC')
    green = rgb('#DCFCE7'); green_text = rgb('#166534'); red = rgb('#FEE2E2'); red_text = rgb('#991B1B')
    gray = rgb('#E2E8F0')

    requests = []
    # BASE_DASH format, filter, widths and conditional rules.
    requests += [
        {'repeatCell': {'range': grid(base_id,0,1,0,22), 'cell': {'userEnteredFormat': {'backgroundColor': dark,'textFormat': {'foregroundColor': white,'bold': True},'horizontalAlignment':'CENTER','verticalAlignment':'MIDDLE','wrapStrategy':'WRAP'}}, 'fields':'userEnteredFormat'}},
        {'repeatCell': {'range': grid(base_id,1,candidate['base_row_count'],0,22), 'cell': {'userEnteredFormat': {'verticalAlignment':'MIDDLE'}}, 'fields':'userEnteredFormat.verticalAlignment'}},
        {'repeatCell': {'range': grid(base_id,1,candidate['base_row_count'],1,2), 'cell': {'userEnteredFormat': {'numberFormat': {'type':'DATE','pattern':'dd/mm/yyyy'}}}, 'fields':'userEnteredFormat.numberFormat'}},
        {'repeatCell': {'range': grid(base_id,1,candidate['base_row_count'],11,19), 'cell': {'userEnteredFormat': {'numberFormat': {'type':'NUMBER','pattern':'$#,##0.00;[Red]($#,##0.00)'}}}, 'fields':'userEnteredFormat.numberFormat'}},
        {'repeatCell': {'range': grid(base_id,1,candidate['base_row_count'],19,21), 'cell': {'userEnteredFormat': {'numberFormat': {'type':'PERCENT','pattern':'0.00%'}}}, 'fields':'userEnteredFormat.numberFormat'}},
        {'setBasicFilter': {'filter': {'range': grid(base_id,0,candidate['base_row_count'],0,22)}}},
        {'addConditionalFormatRule': {'index':0,'rule': {'ranges':[grid(base_id,1,candidate['base_row_count'],18,19)],'booleanRule': {'condition': {'type':'NUMBER_LESS','values':[{'userEnteredValue':'0'}]},'format': {'backgroundColor':red,'textFormat':{'foregroundColor':red_text,'bold':True}}}}}},
        {'addConditionalFormatRule': {'index':1,'rule': {'ranges':[grid(base_id,1,candidate['base_row_count'],18,19)],'booleanRule': {'condition': {'type':'NUMBER_GREATER','values':[{'userEnteredValue':'0'}]},'format': {'backgroundColor':green,'textFormat':{'foregroundColor':green_text}}}}}},
        {'addConditionalFormatRule': {'index':2,'rule': {'ranges':[grid(base_id,1,candidate['base_row_count'],20,21)],'booleanRule': {'condition': {'type':'NUMBER_LESS','values':[{'userEnteredValue':'0'}]},'format': {'backgroundColor':red,'textFormat':{'foregroundColor':red_text,'bold':True}}}}}},
        {'updateDimensionProperties': {'range': {'sheetId':base_id,'dimension':'ROWS','startIndex':0,'endIndex':1},'properties':{'pixelSize':42},'fields':'pixelSize'}},
        {'updateDimensionProperties': {'range': {'sheetId':base_id,'dimension':'COLUMNS','startIndex':0,'endIndex':22},'properties':{'pixelSize':120},'fields':'pixelSize'}},
        {'updateDimensionProperties': {'range': {'sheetId':base_id,'dimension':'COLUMNS','startIndex':5,'endIndex':8},'properties':{'pixelSize':180},'fields':'pixelSize'}},
        {'updateDimensionProperties': {'range': {'sheetId':base_id,'dimension':'COLUMNS','startIndex':21,'endIndex':22},'properties':{'pixelSize':230},'fields':'pixelSize'}},
    ]

    # Dashboard merges.
    merge_ranges = [
        (0,1,0,13),(1,2,0,13),(11,12,0,13),(9,10,0,13),
        (3,4,0,3),(4,6,0,3),(3,4,3,6),(4,6,3,6),(3,4,6,9),(4,6,6,9),(3,4,9,12),(4,6,9,12),
        (6,7,0,3),(7,9,0,3),(6,7,3,6),(7,9,3,6),(6,7,6,9),(7,9,6,9),(6,7,9,12),(7,9,9,12),
    ]
    for sr,er,sc,ec in merge_ranges:
        requests.append({'mergeCells': {'range': grid(dash_id,sr,er,sc,ec),'mergeType':'MERGE_ALL'}})

    card_labels = [(3,4,0,3),(3,4,3,6),(3,4,6,9),(3,4,9,12),(6,7,0,3),(6,7,3,6),(6,7,6,9),(6,7,9,12)]
    card_values = [(4,6,0,3),(4,6,3,6),(4,6,6,9),(4,6,9,12),(7,9,0,3),(7,9,3,6),(7,9,6,9),(7,9,9,12)]
    requests += [
        {'repeatCell': {'range':grid(dash_id,0,1,0,13),'cell':{'userEnteredFormat':{'backgroundColor':dark,'textFormat':{'foregroundColor':white,'bold':True,'fontSize':20},'horizontalAlignment':'CENTER','verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,1,2,0,13),'cell':{'userEnteredFormat':{'backgroundColor':slate,'textFormat':{'foregroundColor':white,'italic':True,'fontSize':11},'horizontalAlignment':'CENTER','verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,11,12,0,13),'cell':{'userEnteredFormat':{'backgroundColor':blue,'textFormat':{'foregroundColor':white,'bold':True,'fontSize':12},'horizontalAlignment':'LEFT','verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,9,10,0,13),'cell':{'userEnteredFormat':{'backgroundColor':light_blue,'textFormat':{'foregroundColor':slate,'italic':True},'wrapStrategy':'WRAP'}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,12,13,0,10),'cell':{'userEnteredFormat':{'backgroundColor':light,'textFormat':{'foregroundColor':slate,'bold':True},'verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,14,15,0,4),'cell':{'userEnteredFormat':{'backgroundColor':dark,'textFormat':{'foregroundColor':white,'bold':True}}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,30,31,0,4),'cell':{'userEnteredFormat':{'backgroundColor':dark,'textFormat':{'foregroundColor':white,'bold':True}}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,64,65,0,4),'cell':{'userEnteredFormat':{'backgroundColor':dark,'textFormat':{'foregroundColor':white,'bold':True}}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,73,74,0,4),'cell':{'userEnteredFormat':{'backgroundColor':dark,'textFormat':{'foregroundColor':white,'bold':True}}},'fields':'userEnteredFormat'}},
        {'repeatCell': {'range':grid(dash_id,15,86,1,4),'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'$#,##0.00;[Red]($#,##0.00)'}}},'fields':'userEnteredFormat.numberFormat'}},
        {'repeatCell': {'range':grid(dash_id,31,64,0,1),'cell':{'userEnteredFormat':{'numberFormat':{'type':'DATE','pattern':'dd/mm'}}},'fields':'userEnteredFormat.numberFormat'}},
        {'repeatCell': {'range':grid(dash_id,4,6,0,12),'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'$#,##0.00;[Red]($#,##0.00)'}}},'fields':'userEnteredFormat.numberFormat'}},
        {'repeatCell': {'range':grid(dash_id,7,9,0,6),'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.00%'}}},'fields':'userEnteredFormat.numberFormat'}},
        {'updateDimensionProperties': {'range':{'sheetId':dash_id,'dimension':'COLUMNS','startIndex':0,'endIndex':13},'properties':{'pixelSize':105},'fields':'pixelSize'}},
        {'updateDimensionProperties': {'range':{'sheetId':dash_id,'dimension':'ROWS','startIndex':0,'endIndex':1},'properties':{'pixelSize':44},'fields':'pixelSize'}},
        {'updateDimensionProperties': {'range':{'sheetId':dash_id,'dimension':'ROWS','startIndex':1,'endIndex':2},'properties':{'pixelSize':30},'fields':'pixelSize'}},
    ]
    for sr,er,sc,ec in card_labels:
        requests.append({'repeatCell': {'range':grid(dash_id,sr,er,sc,ec),'cell':{'userEnteredFormat':{'backgroundColor':blue,'textFormat':{'foregroundColor':white,'bold':True,'fontSize':10},'horizontalAlignment':'CENTER','verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat'}})
    for sr,er,sc,ec in card_values:
        requests.append({'repeatCell': {'range':grid(dash_id,sr,er,sc,ec),'cell':{'userEnteredFormat':{'backgroundColor':white,'borders':{'top':{'style':'SOLID','color':gray},'bottom':{'style':'SOLID','color':gray},'left':{'style':'SOLID','color':gray},'right':{'style':'SOLID','color':gray}},'textFormat':{'foregroundColor':dark,'bold':True,'fontSize':16},'horizontalAlignment':'CENTER','verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat'}})

    # Data validation dropdowns for analytical filters.
    validations = [
        (1, candidate['filters']['partners']), (3, candidate['filters']['statuses']),
        (5, candidate['filters']['gestores']), (7, candidate['filters']['verticals']),
        (9, candidate['filters']['sites']),
    ]
    for col_index, options in validations:
        requests.append({'setDataValidation': {
            'range': grid(dash_id,12,13,col_index,col_index+1),
            'rule': {'condition': {'type':'ONE_OF_LIST','values':[{'userEnteredValue':v} for v in options]},'strict':True,'showCustomUi':True},
        }})

    # Four live charts sourced from the query tables on DASH EXECUTIVO.
    charts = [
        {
            'title':'Top sites por lucro líquido','type':'BAR','domain':(15,27,0,1),'series':[(15,27,3,4)],
            'anchor':(14,5),'width':760,'height':320,'legend':'NO_LEGEND','haxis':'US$','vaxis':'Site'
        },
        {
            'title':'Evolução diária — receita, gastos e lucro','type':'LINE','domain':(31,64,0,1),'series':[(31,64,1,2),(31,64,2,3),(31,64,3,4)],
            'anchor':(31,5),'width':760,'height':340,'legend':'BOTTOM_LEGEND','haxis':'Data','vaxis':'US$'
        },
        {
            'title':'Resultado por parceiro','type':'COLUMN','domain':(65,72,0,1),'series':[(65,72,1,2),(65,72,2,3),(65,72,3,4)],
            'anchor':(49,5),'width':760,'height':300,'legend':'BOTTOM_LEGEND','haxis':'Parceiro','vaxis':'US$'
        },
        {
            'title':'Lucro líquido por país','type':'BAR','domain':(74,86,0,1),'series':[(74,86,3,4)],
            'anchor':(65,5),'width':760,'height':320,'legend':'NO_LEGEND','haxis':'US$','vaxis':'País'
        },
    ]
    for chart in charts:
        basic = {
            'chartType': chart['type'], 'legendPosition': chart['legend'], 'headerCount': 1,
            'axis': [{'position':'BOTTOM_AXIS','title':chart['haxis']},{'position':'LEFT_AXIS','title':chart['vaxis']}],
            'domains': [{'domain': series_range(dash_id,*chart['domain'])}],
            'series': [
                {'series': series_range(dash_id,*s), 'targetAxis':'BOTTOM_AXIS' if chart['type']=='BAR' else 'LEFT_AXIS'}
                for s in chart['series']
            ],
        }
        requests.append({'addChart': {'chart': {
            'spec': {'title':chart['title'],'titleTextFormat':{'bold':True,'fontSize':12},'backgroundColor':white,'basicChart':basic},
            'position': {'overlayPosition': {'anchorCell': {'sheetId':dash_id,'rowIndex':chart['anchor'][0],'columnIndex':chart['anchor'][1]},'offsetXPixels':8,'offsetYPixels':8,'widthPixels':chart['width'],'heightPixels':chart['height']}},
        }}})

    batch_update(requests)

    # Poll live formulas/values until dependent formulas and QUERY spills settle.
    base_formula = base_value = base_formatted = dash_formula = dash_value = dash_formatted = None
    all_errors = []
    for _ in range(8):
        base_formula = values_get(f"'BASE_DASH'!A1:V{candidate['base_row_count']}", 'FORMULA')
        base_value = values_get(f"'BASE_DASH'!A1:V{candidate['base_row_count']}", 'UNFORMATTED_VALUE')
        base_formatted = values_get(f"'BASE_DASH'!A1:V{candidate['base_row_count']}", 'FORMATTED_VALUE')
        dash_formula = values_get("'DASH EXECUTIVO'!A1:M90", 'FORMULA')
        dash_value = values_get("'DASH EXECUTIVO'!A1:M90", 'UNFORMATTED_VALUE')
        dash_formatted = values_get("'DASH EXECUTIVO'!A1:M90", 'FORMATTED_VALUE')
        all_errors = []
        for label, data in [('BASE_DASH',base_formatted),('DASH EXECUTIVO',dash_formatted)]:
            for r,row in enumerate(data,1):
                for c,value in enumerate(row,1):
                    if isinstance(value,str) and value.startswith('#'):
                        all_errors.append(f'{label}!{r},{c}:{value}')
        if not all_errors and cell(dash_formatted,16,1) == 'Site' and cell(dash_formatted,32,1) == 'Data':
            break
        time.sleep(2)
    if any(x is None for x in [base_formula,base_value,base_formatted,dash_formula,dash_value,dash_formatted]):
        raise RuntimeError('dashboard readback unavailable')
    assert base_formula is not None and base_value is not None and base_formatted is not None
    assert dash_formula is not None and dash_value is not None and dash_formatted is not None
    if all_errors:
        raise RuntimeError(f'dashboard displayed errors: {all_errors[:20]}')

    # Exact base candidate readback, including every formula and static dimension.
    base_mismatches = []
    for r, expected_row in enumerate(candidate['base_rows'],1):
        for c, expected in enumerate(expected_row,1):
            actual = cell(base_formula,r,c)
            if actual != expected:
                base_mismatches.append({'row':r,'col':c,'expected':expected,'actual':actual})
                if len(base_mismatches) >= 20: break
        if len(base_mismatches) >= 20: break
    if base_mismatches:
        raise RuntimeError(f'BASE_DASH formula/static mismatch: {base_mismatches}')

    # Exact dashboard anchor formula/label readback.
    dash_anchor_mismatches = []
    for a1, values in candidate['dashboard_values'].items():
        m = re.fullmatch(r'([A-Z]+)(\d+)', a1)
        if not m: raise RuntimeError(f'invalid dashboard anchor: {a1}')
        cnum = 0
        for ch in m.group(1): cnum = cnum*26 + ord(ch)-64
        expected = values[0][0]
        actual = cell(dash_formula,int(m.group(2)),cnum)
        if actual != expected:
            dash_anchor_mismatches.append({'cell':a1,'expected':expected,'actual':actual})
    if dash_anchor_mismatches:
        raise RuntimeError(f'DASH EXECUTIVO anchor mismatch: {dash_anchor_mismatches[:10]}')

    # Source tabs must remain byte-equivalent in FORMULA mode.
    source_formula_after = values_get("'Agosto 2026'!A1:APE338", 'FORMULA')
    caixa_formula_after = values_get("'CAIXA SINTETICO'!A1:R85", 'FORMULA')
    if formula_hash(source_formula_after) != candidate['source_formula_hashes']['Agosto 2026']:
        raise RuntimeError('Agosto 2026 changed during dashboard build')
    if formula_hash(caixa_formula_after) != candidate['source_formula_hashes']['CAIXA SINTETICO']:
        raise RuntimeError('CAIXA SINTETICO changed during dashboard build')

    # Recompute normalized-base parity against live helper totals.
    helper = values_get("'Agosto 2026'!AOW36:APE36", 'UNFORMATTED_VALUE')
    helper_row = helper[0]
    site_rows = [row for row in base_value[1:] if len(row) >= 19 and row[2] == 'SITE']
    daily_rows = [row for row in base_value[1:] if len(row) >= 21 and row[2] == 'GERAL']
    month_rows = [row for row in base_value[1:] if len(row) >= 21 and row[2] == 'GERAL_MÊS']
    if len(site_rows) != 43 or len(daily_rows) != 31 or len(month_rows) != 1:
        raise RuntimeError(f'normalized row counts drifted: site={len(site_rows)} daily={len(daily_rows)} month={len(month_rows)}')
    def total(rows, idx): return sum(float(row[idx] or 0) for row in rows)
    parity = {
        'site_net': close(total(site_rows,13), helper_row[0]),
        'site_tax': close(total(site_rows,14), helper_row[1]),
        'site_company_expense': close(total(site_rows,15), helper_row[2]),
        'site_spend': close(total(site_rows,17), helper_row[5]),
        'site_profit_identity': close(total(site_rows,18), float(helper_row[0])+float(helper_row[1])+float(helper_row[2])+float(helper_row[5])),
        'daily_net': close(total(daily_rows,13), helper_row[0]),
        'daily_tax': close(total(daily_rows,14), helper_row[1]),
        'daily_company_expense': close(total(daily_rows,15), helper_row[2]),
        'daily_employee_expense': close(total(daily_rows,16), helper_row[3]),
        'daily_invalid': close(total(daily_rows,12), helper_row[4]),
        'daily_spend': close(total(daily_rows,17), helper_row[5]),
        'daily_profit': close(total(daily_rows,18), helper_row[6]),
    }
    failed_parity = [k for k,v in parity.items() if not v]
    if failed_parity:
        raise RuntimeError(f'normalized source parity failed: {failed_parity}')

    caixa_values = values_get("'CAIXA SINTETICO'!J2:J81", 'UNFORMATTED_VALUE')
    j = lambda row: cell(caixa_values,row-1,1)
    monthly = month_rows[0]
    monthly_checks = {
        'gross': close(monthly[11],j(58)), 'invalid': close(monthly[12],sum(float(j(r) or 0) for r in range(59,63))),
        'net_after_invalid': close(monthly[13],j(64)), 'tax': close(monthly[14],j(71)),
        'company_expense': close(monthly[15],j(72)), 'employee_expense': close(monthly[16],j(73)),
        'spend': close(monthly[17],j(75)), 'profit': close(monthly[18],j(77)), 'roi_net': close(monthly[20],j(79)),
    }
    if not all(monthly_checks.values()):
        raise RuntimeError(f'monthly closure row mismatch: {[k for k,v in monthly_checks.items() if not v]}')

    active_sites_value = cell(dash_value,8,7)
    profitable_sites_value = cell(dash_value,8,10)
    dashboard_checks = {
        'gross': close(cell(dash_value,5,1),j(58)),
        'net_after_invalid': close(cell(dash_value,5,4),j(64)),
        'spend_positive': close(cell(dash_value,5,7),-float(j(75))),
        'profit': close(cell(dash_value,5,10),j(77)),
        'roi_net': close(cell(dash_value,8,1),j(79)),
        'invalid_rate': close(cell(dash_value,8,4),-sum(float(j(r) or 0) for r in range(59,63))/float(j(58))),
        'active_sites_positive': isinstance(active_sites_value,(int,float)) and float(active_sites_value) > 0,
        'profitable_sites_nonnegative': isinstance(profitable_sites_value,(int,float)) and float(profitable_sites_value) >= 0,
        'top_sites_table': cell(dash_formatted,16,1) == 'Site' and cell(dash_formatted,17,1) not in ('','Sem dados para os filtros'),
        'daily_table': cell(dash_formatted,32,1) == 'Data' and len([r for r in dash_formatted[32:64] if r]) >= 31,
        'partner_table': cell(dash_formatted,66,1) == 'Parceiro',
        'country_table': cell(dash_formatted,75,1) == 'País',
    }
    if not all(dashboard_checks.values()):
        raise RuntimeError(f'dashboard checks failed: {[k for k,v in dashboard_checks.items() if not v]}')

    final_meta = metadata_get('spreadsheetId,properties,sheets(properties,charts,basicFilter)')
    final_sheets = final_meta.get('sheets') or []
    final_titles = [s['properties']['title'] for s in final_sheets]
    expected_titles = [s['properties']['title'] for s in backup['metadata']['sheets']] + ['BASE_DASH','DASH EXECUTIVO']
    if sorted(final_titles) != sorted(expected_titles) or len(final_titles) != len(expected_titles):
        raise RuntimeError('unexpected workbook sheet set after build')
    base_meta = next(s for s in final_sheets if s['properties']['title']=='BASE_DASH')
    dash_meta = next(s for s in final_sheets if s['properties']['title']=='DASH EXECUTIVO')
    if not base_meta.get('basicFilter'):
        raise RuntimeError('BASE_DASH basic filter missing on readback')
    if len(dash_meta.get('charts') or []) != 4:
        raise RuntimeError(f"chart readback mismatch: {len(dash_meta.get('charts') or [])}")

    validation_meta = metadata_get(
        'sheets(properties(sheetId,title),data(startRow,startColumn,rowData.values.dataValidation))',
        include_grid=True,
        ranges=["'DASH EXECUTIVO'!B13","'DASH EXECUTIVO'!D13","'DASH EXECUTIVO'!F13","'DASH EXECUTIVO'!H13","'DASH EXECUTIVO'!J13"],
    )
    validation_sheet = next(s for s in validation_meta.get('sheets') or [] if s['properties']['title']=='DASH EXECUTIVO')
    validation_blocks = validation_sheet.get('data') or []
    validation_count = 0
    for block in validation_blocks:
        rows = block.get('rowData') or []
        values = (rows[0].get('values') or []) if rows else []
        rule = (values[0].get('dataValidation') or {}) if values else {}
        cond = rule.get('condition') or {}
        if cond.get('type') == 'ONE_OF_LIST' and (cond.get('values') or [{}])[0].get('userEnteredValue') == 'TODOS':
            validation_count += 1
    if validation_count != 5:
        raise RuntimeError(f'filter data-validation readback mismatch: {validation_count}/5')

    verification = {
        'status':'pass','verified_at':datetime.now(timezone.utc).isoformat(),'spreadsheet_id':SHEET_ID,
        'spreadsheet_url':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
        'backup_path':str(BACKUP_PATH),'backup_sha256':hashlib.sha256(BACKUP_PATH.read_bytes()).hexdigest(),
        'candidate_path':str(CANDIDATE_PATH),'candidate_sha256':hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest(),
        'structural_canary':{'title':canary_title,'added':True,'readback':True,'deleted':canary_deleted,'absent_after':True},
        'created_sheets':{'BASE_DASH':base_id,'DASH EXECUTIVO':dash_id},
        'base_rows':candidate['base_row_count'],'site_segments':43,'country_rows':78,'daily_rows':31,'monthly_rows':1,
        'source_formula_hashes_unchanged':True,'source_displayed_errors':0,'dashboard_displayed_errors':0,
        'base_formula_mismatches':[],'dashboard_anchor_mismatches':[],
        'parity_checks':parity,'monthly_checks':monthly_checks,'dashboard_checks':dashboard_checks,
        'basic_filter_readback':True,'data_validation_readback':'5/5','chart_readback':'4/4',
        'dashboard_values':{'gross':j(58),'net_after_invalid':j(64),'spend_positive':-float(j(75)),'profit':j(77),'roi_net':j(79),'invalid_rate':cell(dash_value,8,4),'active_sites':cell(dash_value,8,7),'profitable_sites':cell(dash_value,8,10)},
        'rollback':{'type':'delete_created_sheets_only','sheet_ids':[base_id,dash_id],'source_tabs_untouched':True},
    }
    verification_path = WORK / 'dashboard-august-final-verification.json'
    verification_sha = write_json(verification_path, verification)
    result_path = WORK / 'dashboard-august-build-result.json'
    result_sha = write_json(result_path, {
        'status':'pass','created_sheets':verification['created_sheets'],'chart_count':4,'data_validations':5,
        'verification_path':str(verification_path),'verification_sha256':verification_sha,
        'source_tabs_untouched':True,'rollback_sheet_ids':[base_id,dash_id],
    })
    print(json.dumps({
        'status':'pass','created_sheets':verification['created_sheets'],'base_rows':candidate['base_row_count'],
        'charts':4,'filters':5,'source_tabs_untouched':True,'displayed_errors':0,
        'gross':j(58),'net_after_invalid':j(64),'spend':-float(j(75)),'profit':j(77),'roi_net':j(79),
        'active_sites':cell(dash_value,8,7),'profitable_sites':cell(dash_value,8,10),
        'url':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={dash_id}',
        'verification_path':str(verification_path),'verification_sha256':verification_sha,'result_sha256':result_sha,
    }, ensure_ascii=False, separators=(',',':')))
except Exception:
    # Roll back only sheets created by this run. Source tabs are never mutated.
    if created_ids:
        try:
            batch_update([{'deleteSheet': {'sheetId': sid}} for sid in created_ids])
        except Exception:
            pass
        remaining = [s['properties']['title'] for s in metadata_get('sheets.properties').get('sheets') or []]
        if 'BASE_DASH' in remaining or 'DASH EXECUTIVO' in remaining:
            raise RuntimeError('dashboard build failed and rollback is incomplete')
    raise
