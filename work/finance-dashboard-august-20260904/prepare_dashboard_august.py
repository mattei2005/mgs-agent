#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/root/mgs-agent')
WORK = BASE / 'work/finance-dashboard-august-20260904'
SHEET_ID = '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
HELPER = BASE / 'scripts/mgs_google_workspace_auth.py'
BLOCKS_PATH = WORK / 'august-site-blocks.json'
TARGET_TABS = {'BASE_DASH', 'DASH EXECUTIVO'}

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
        raise RuntimeError(f'Google API failure: {err}')
    return data


def values_get(a1: str, render: str):
    encoded = urllib.parse.quote(a1, safe='')
    data = api('GET', (
        f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{encoded}'
        f'?majorDimension=ROWS&valueRenderOption={render}'
    ))
    return data.get('values') or []


def write_json(path: Path, obj):
    raw = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    path.write_text(raw, encoding='utf-8')
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def colnum(name: str) -> int:
    n = 0
    for ch in name:
        n = n * 26 + ord(ch.upper()) - 64
    return n


def colname(n: int) -> str:
    out = ''
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def cell(grid, row: int, col: int):
    if row < 1 or col < 1 or row > len(grid):
        return ''
    values = grid[row - 1]
    return values[col - 1] if col <= len(values) else ''


def ref(col: int, row: int) -> str:
    return f"'Agosto 2026'!{colname(col)}{row}"


def formula_ref(col: int, row: int) -> str:
    return '=' + ref(col, row)


def formula_sum(cols: list[int], row: int) -> str:
    refs = ','.join(ref(col, row) for col in cols)
    return f'=SUM({refs})'


def source_formula_hash(grid) -> str:
    raw = json.dumps(grid, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

metadata = api('GET', (
    f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}'
    '?includeGridData=false&fields=spreadsheetId,properties,sheets.properties'
))
sheets = metadata.get('sheets') or []
titles = [((s.get('properties') or {}).get('title')) for s in sheets]
if TARGET_TABS.intersection(titles):
    raise RuntimeError(f'dashboard target tab already exists: {sorted(TARGET_TABS.intersection(titles))}')
if 'Agosto 2026' not in titles or 'CAIXA SINTETICO' not in titles:
    raise RuntimeError('canonical source tabs missing')

source_range = "'Agosto 2026'!A1:APE338"
caixa_range = "'CAIXA SINTETICO'!A1:R85"
source = {
    'formula': values_get(source_range, 'FORMULA'),
    'unformatted': values_get(source_range, 'UNFORMATTED_VALUE'),
    'formatted': values_get(source_range, 'FORMATTED_VALUE'),
}
caixa = {
    'formula': values_get(caixa_range, 'FORMULA'),
    'unformatted': values_get(caixa_range, 'UNFORMATTED_VALUE'),
    'formatted': values_get(caixa_range, 'FORMATTED_VALUE'),
}

# Fail closed on visible formula errors in either approved source tab.
errors = []
for sheet_name, grid in [('Agosto 2026', source['formatted']), ('CAIXA SINTETICO', caixa['formatted'])]:
    for r, row in enumerate(grid, 1):
        for c, value in enumerate(row, 1):
            if isinstance(value, str) and value.startswith('#'):
                errors.append(f'{sheet_name}!{colname(c)}{r}:{value}')
if errors:
    raise RuntimeError(f'source displayed errors: {errors[:20]}')

# Current correction and closure invariants.
if cell(source['formula'], 23, colnum('CR')) != '=IF(CQ23="","",-CQ23*$J$1)':
    raise RuntimeError('CR23 correction drifted')
for r in range(5, 36):
    if cell(source['formula'], r, colnum('AGT')) != f'=SUM(AGN{r})':
        raise RuntimeError(f'AGT correction drifted at row {r}')
expected_summary = {
    'BF38': '=SUM(BG36,BP36,BY36)',
    'OX38': '=SUM(OY36,PH36,PQ36)',
    'RR38': '=SUM(RS36,SB36,SK36,RS136,SB136,SK136)',
    'AGK38': '=SUM(AGL36)',
}
for a1, expected in expected_summary.items():
    m = re.fullmatch(r'([A-Z]+)(\d+)', a1)
    if not m:
        raise RuntimeError(f'invalid summary cell token: {a1}')
    if cell(source['formula'], int(m.group(2)), colnum(m.group(1))) != expected:
        raise RuntimeError(f'row-38 summary drifted: {a1}')
caixa_expected = {
    'J58': '=SUM(J9:J57)',
    'J59': "=SUM('Agosto 2026'!P175)",
    'J60': "=SUM('Agosto 2026'!P176)",
    'J61': "=SUM('Agosto 2026'!P177)",
    'J62': "=SUM('Agosto 2026'!P178)",
    'J64': '=SUM(J58:J63)',
    'J67': '=SUM(J12:J35,J59)*$B$3*-1',
    'J68': '=SUM(J53:J54,J60)*$B$4*-1',
    'J69': '=SUM(J9:J10,J61)*$B$3*-1',
    'J70': '=SUM(J38:J51,J62)*$B$3*-1',
    'J71': '=SUM(J64:J70)*$B$2*-1',
    'J72': "=SUM('Agosto 2026'!O145)",
    'J73': "=SUM('Agosto 2026'!O161)",
    'J75': "=SUM('Agosto 2026'!APB36)",
    'J77': '=SUM(J64:J76)',
    'J80': '=SUM(J77)*50%',
    'J81': '=SUM(J80*J2)',
}
for a1, expected in caixa_expected.items():
    row = int(a1[1:])
    if cell(caixa['formula'], row, 10) != expected:
        raise RuntimeError(f'CAIXA closure drifted: {a1}')
if not str(cell(caixa['formula'], 79, 10)).startswith('=IFERROR(J77/-J75'):
    raise RuntimeError('CAIXA J79 closure drifted')

blocks = json.loads(BLOCKS_PATH.read_text(encoding='utf-8'))
if len(blocks) != 41:
    raise RuntimeError('expected 41 August top blocks')

partner_by_start = {}
for start in ['FX', 'GP']:
    partner_by_start[start] = 'YMonetize'
for start in ['D','V','AN','BF','CP','FF','JA','KB','MV','OF','OX','QH','QZ','KT','MD','HH','II','UC','VD','RR','TB','YG','YY']:
    partner_by_start[start] = 'ActiveView'
for start in ['AGK','AHC','AFJ','ABF','ACP','WE','ADZ','ZQ','AID','AIV','AJM','AKD','AKU','ALL']:
    partner_by_start[start] = 'JBF'
for start in ['EG','DH']:
    partner_by_start[start] = 'M2'
if set(partner_by_start) != {b['start'] for b in blocks}:
    raise RuntimeError('partner map does not cover all August blocks')

manager_sets = {
    'FinanceTopFeed': ['Joe'], 'TopFeed Finanzas': ['Joe'],
    'Infinitynexx': ['George', 'Joe'],
    'Newsoun': ['Kelly'], 'Newsoun Finanzas': ['Kelly'], 'Newsoun DE': ['Kelly'], 'Helixenit': ['Kelly'],
    'Ducapes': ['George'], 'Ducapes Finance': ['George'], 'Wantabrand US-CC-ES': ['George'],
    'Wantabrand BR-CAR-BR': ['George'], 'Wantabrand Finance': ['George'], 'Marevelx': ['George'],
    'Openzed': ['George', 'Isliago'], 'Openzed Finanzas': ['Isliago'], 'Zytiva': ['Isliago'],
    'Zytiva Finanzas': ['Isliago'], 'Xyvlov': ['Isliago'], 'WavesBee': ['Isliago'],
    'Eggbev': ['Nicolas'], 'Eggbev Finanzas': ['Nicolas'], 'Lyzmo': ['Nicolas'],
    'Lyzmo Finanzas': ['Nicolas'], 'SPE': ['Nicolas'], 'FinanceAdx': ['Nicolas'],
    'Fincgriffin': ['George', 'Isliago', 'Joe', 'Kelly', 'Nicolas'],
    'CreditoParaVeiculo': ['George', 'Isliago', 'Joe', 'Kelly', 'Nicolas'],
}


def manager_fields(site_names: list[str]):
    names = sorted({name for site in site_names for name in manager_sets.get(site, [])})
    if not names:
        return 'NÃO MAPEADO', ''
    if len(names) == 1:
        return names[0], names[0]
    return 'COMPARTILHADO', ', '.join(names)


def vertical(site: str) -> str:
    low = site.lower()
    if 'us-cc-' in low:
        return 'CC'
    if 'br-car-' in low or any(x in low for x in ['creditoparaveiculo', 'financiamentoauto', 'autocredit', 'carcredit']):
        return 'CAR'
    if 'gaming' in low or 'gamezone' in low:
        return 'GAMING'
    if 'jobs' in low:
        return 'JOBS'
    return 'NÃO CLASSIFICADO'

headers = [
    'Mês','Data','Nível','Segmento','Parceiro','Site','Gestor','Gestores','Status','País','Vertical',
    'Receita Bruta USD','Tráfego Inválido USD','Receita Líquida USD','Imposto USD',
    'Despesa Empresa USD','Despesa Funcionários USD','Gastos USD','Lucro Líquido USD','ROI Gross','ROI Líquido','Fonte'
]
base_rows = [headers]
segment_specs = []

for block in blocks:
    start, end = colnum(block['start']), colnum(block['end'])
    status = block['status']
    if cell(source['formula'], 1, end) != status:
        raise RuntimeError(f"block status/header mismatch at {block['end']}")
    top_headers = {str(cell(source['formula'], 2, c)): c for c in range(start, end + 1) if cell(source['formula'], 2, c) not in ('', None)}
    if top_headers.get('ROI_NET_TOTAL') != end or 'RECEITA_NET_TOTAL' not in top_headers:
        raise RuntimeError(f"top block metric family mismatch: {block['start']}:{block['end']}")
    segment_specs.append((block, 2, 36, 'PRINCIPAL', top_headers))
    lower_headers = {str(cell(source['formula'], 102, c)): c for c in range(start, end + 1) if cell(source['formula'], 102, c) not in ('', None)}
    if 'RECEITA_NET_TOTAL' in lower_headers:
        if lower_headers.get('ROI_NET_TOTAL') != end:
            raise RuntimeError(f"lower block metric family mismatch: {block['start']}:{block['end']}")
        segment_specs.append((block, 102, 136, 'ICARO - G001-D', lower_headers))

if len(segment_specs) != 43:
    raise RuntimeError(f'expected 43 monthly site segments, found {len(segment_specs)}')

all_gross_daily_specs = []
for block, header_row, total_row, segment_name, hmap in segment_specs:
    partner = partner_by_start[block['start']]
    status = block['status']
    site_names = block['site_names']
    site_label = ' + '.join(site_names)
    gestor, gestores = manager_fields(site_names)
    countries = list(block['countries'])
    # Re-discover countries from metric headers; require exact artifact parity.
    discovered = sorted({m.group(1) for h in hmap for m in [re.fullmatch(r'(?:GROSS_USD|GROSS_CAD|GROSS|INVALIDO|NET_USD|NET|IMPOSTO|GASTOS|LUCRO_LIQUIDO|ROI_GROSS|ROI_NET)_([A-Z]{2})', h)] if m})
    if sorted(countries) != discovered:
        raise RuntimeError(f"country/header mismatch for {block['start']}: {countries} vs {discovered}")
    gross_cols = []
    for country in countries:
        gross_col = hmap.get(f'GROSS_USD_{country}') or hmap.get(f'GROSS_{country}')
        if not gross_col:
            raise RuntimeError(f"USD gross source missing for {block['start']} {country}")
        gross_cols.append(gross_col)
    all_gross_daily_specs.append((gross_cols, 5 if header_row == 2 else 105))
    total = lambda name: hmap[name]
    base_rows.append([
        'Agosto 2026','=DATE(2026,8,31)','SITE',segment_name,partner,site_label,gestor,gestores,status,'TODOS',
        'MÚLTIPLA' if len(site_names) > 1 else vertical(site_label),
        formula_sum(gross_cols, total_row), formula_ref(total('INVALIDO_TOTAL'), total_row),
        formula_ref(total('RECEITA_NET_TOTAL'), total_row), formula_ref(total('IMPOSTO_TOTAL'), total_row),
        formula_ref(total('DESPESA_TOTAL'), total_row), '', formula_ref(total('GASTOS_TOTAL'), total_row),
        formula_ref(total('LUCRO_LIQUIDO_TOTAL'), total_row), formula_ref(total('ROI_GROSS_TOTAL'), total_row),
        formula_ref(total('ROI_NET_TOTAL'), total_row), f"Agosto 2026!{block['start']}:{block['end']} linha {total_row}"
    ])
    for country in countries:
        country_site = site_label
        if len(site_names) > 1:
            if country == 'US': country_site = 'Wantabrand US-CC-ES'
            elif country == 'BR': country_site = 'Wantabrand BR-CAR-BR'
        cg, cgs = manager_fields([country_site])
        def metric(*names):
            for name in names:
                if name in hmap: return hmap[name]
            raise RuntimeError(f"metric missing for {block['start']} {country}: {names}")
        gross_col = metric(f'GROSS_USD_{country}', f'GROSS_{country}')
        base_rows.append([
            'Agosto 2026','=DATE(2026,8,31)','PAÍS',segment_name,partner,country_site,cg,cgs,status,country,vertical(country_site),
            formula_ref(gross_col,total_row), formula_ref(metric(f'INVALIDO_{country}'),total_row),
            formula_ref(metric(f'NET_USD_{country}',f'NET_{country}'),total_row), formula_ref(metric(f'IMPOSTO_{country}'),total_row),
            '', '', formula_ref(metric(f'GASTOS_{country}'),total_row), formula_ref(metric(f'LUCRO_LIQUIDO_{country}'),total_row),
            formula_ref(metric(f'ROI_GROSS_{country}'),total_row), formula_ref(metric(f'ROI_NET_{country}'),total_row),
            f"Agosto 2026!{block['start']}:{block['end']} linha {total_row}"
        ])

# Daily global rows use the validated helper columns and include lower blocks.
for source_row in range(5, 36):
    gross_refs = []
    for gross_cols, first_row in all_gross_daily_specs:
        row = source_row if first_row == 5 else source_row + 100
        gross_refs.extend(ref(c, row) for c in gross_cols)
    base_rows.append([
        'Agosto 2026',f"='Agosto 2026'!B{source_row}",'GERAL','DIA','TODOS','TODOS','MGS','MGS','PROVISÓRIO','TODOS','TODAS',
        '=SUM(' + ','.join(gross_refs) + ')', formula_ref(colnum('APA'),source_row), formula_ref(colnum('AOW'),source_row),
        formula_ref(colnum('AOX'),source_row), formula_ref(colnum('AOY'),source_row), formula_ref(colnum('AOZ'),source_row),
        formula_ref(colnum('APB'),source_row), formula_ref(colnum('APC'),source_row), formula_ref(colnum('APD'),source_row),
        formula_ref(colnum('APE'),source_row), f'Agosto 2026!AOW{source_row}:APE{source_row}'
    ])

# One authoritative monthly closure row from CAIXA SINTETICO.
monthly_row_number = len(base_rows) + 1
base_rows.append([
    'Agosto 2026','=DATE(2026,8,31)','GERAL_MÊS','MÊS','TODOS','TODOS','MGS','MGS','PROVISÓRIO','TODOS','TODAS',
    "='CAIXA SINTETICO'!J58", "=SUM('CAIXA SINTETICO'!J59:J62)", "='CAIXA SINTETICO'!J64",
    "='CAIXA SINTETICO'!J71", "='CAIXA SINTETICO'!J72", "='CAIXA SINTETICO'!J73",
    "='CAIXA SINTETICO'!J75", "='CAIXA SINTETICO'!J77", f'=IFERROR(L{monthly_row_number}/ABS(R{monthly_row_number})-1,"")',
    "='CAIXA SINTETICO'!J79", 'CAIXA SINTETICO!J58:J79'
])

# Dashboard sparse write payload. QUERY outputs spill into blank table areas.
dashboard_values = {
    'A1': [['MGS | DASHBOARD FINANCEIRO']],
    'A2': [['Agosto 2026 • PROVISÓRIO até a confirmação das taxas de pagamento']],
    'A4': [['RECEITA BRUTA']], 'A5': [["='CAIXA SINTETICO'!J58"]],
    'D4': [['RECEITA APÓS INVÁLIDOS']], 'D5': [["='CAIXA SINTETICO'!J64"]],
    'G4': [['GASTOS DE MÍDIA']], 'G5': [["=-'CAIXA SINTETICO'!J75"]],
    'J4': [['LUCRO LÍQUIDO']], 'J5': [["='CAIXA SINTETICO'!J77"]],
    'A7': [['ROI LÍQUIDO']], 'A8': [["='CAIXA SINTETICO'!J79"]],
    'D7': [['TRÁFEGO INVÁLIDO']], 'D8': [["=IFERROR(-SUM('CAIXA SINTETICO'!J59:J62)/'CAIXA SINTETICO'!J58,\"\")"]],
    'G7': [['SITES ATIVOS']], 'G8': [['=COUNTUNIQUE(FILTER(BASE_DASH!F2:F,BASE_DASH!C2:C="SITE",BASE_DASH!I2:I="ATIVO"))']],
    'J7': [['SITES LUCRATIVOS']], 'J8': [['=COUNTIF(QUERY(FILTER({BASE_DASH!F2:F,BASE_DASH!S2:S},BASE_DASH!C2:C="SITE",BASE_DASH!I2:I="ATIVO"),"select Col1,sum(Col2) group by Col1 label sum(Col2) \'\'",0),">0")']],
    'A10': [['Fonte executiva: CAIXA SINTETICO coluna J; análises por site/país: Agosto 2026. O mês permanece provisório.']],
    'A12': [['FILTROS DAS ANÁLISES']],
    'A13': [['Parceiro']], 'B13': [['TODOS']], 'C13': [['Status']], 'D13': [['TODOS']],
    'E13': [['Gestor']], 'F13': [['TODOS']], 'G13': [['Vertical']], 'H13': [['TODOS']],
    'I13': [['Site']], 'J13': [['TODOS']],
    'A15': [['TOP SITES POR LUCRO LÍQUIDO']],
    'A16': [[
        '=IFERROR(QUERY(FILTER({BASE_DASH!F2:F,BASE_DASH!N2:N,-BASE_DASH!R2:R,BASE_DASH!S2:S},BASE_DASH!C2:C="SITE",IF($B$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!E2:E=$B$13),IF($D$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!I2:I=$D$13),IF($F$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!G2:G=$F$13),IF($H$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!K2:K=$H$13),IF($J$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!F2:F=$J$13)),"select Col1,sum(Col2),sum(Col3),sum(Col4) group by Col1 order by sum(Col4) desc limit 10 label Col1 \'Site\',sum(Col2) \'Receita líquida\',sum(Col3) \'Gastos\',sum(Col4) \'Lucro líquido\'",0),"Sem dados para os filtros")'
    ]],
    'A31': [['EVOLUÇÃO DIÁRIA GLOBAL']],
    'A32': [[
        '=QUERY(FILTER({BASE_DASH!B2:B,BASE_DASH!N2:N,-BASE_DASH!R2:R,BASE_DASH!S2:S},BASE_DASH!C2:C="GERAL"),"select Col1,Col2,Col3,Col4 order by Col1 label Col1 \'Data\',Col2 \'Receita líquida\',Col3 \'Gastos\',Col4 \'Lucro líquido\'",0)'
    ]],
    'A65': [['RESULTADO POR PARCEIRO']],
    'A66': [[
        '=IFERROR(QUERY(FILTER({BASE_DASH!E2:E,BASE_DASH!N2:N,-BASE_DASH!R2:R,BASE_DASH!S2:S},BASE_DASH!C2:C="SITE",IF($B$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!E2:E=$B$13),IF($D$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!I2:I=$D$13),IF($F$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!G2:G=$F$13),IF($H$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!K2:K=$H$13),IF($J$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!F2:F=$J$13)),"select Col1,sum(Col2),sum(Col3),sum(Col4) group by Col1 order by sum(Col4) desc label Col1 \'Parceiro\',sum(Col2) \'Receita líquida\',sum(Col3) \'Gastos\',sum(Col4) \'Lucro líquido\'",0),"Sem dados para os filtros")'
    ]],
    'A74': [['RESULTADO POR PAÍS']],
    'A75': [[
        '=IFERROR(QUERY(FILTER({BASE_DASH!J2:J,BASE_DASH!N2:N,-BASE_DASH!R2:R,BASE_DASH!S2:S},BASE_DASH!C2:C="PAÍS",IF($B$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!E2:E=$B$13),IF($D$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!I2:I=$D$13),IF($F$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!G2:G=$F$13),IF($H$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!K2:K=$H$13),IF($J$13="TODOS",BASE_DASH!F2:F<>"",BASE_DASH!F2:F=$J$13)),"select Col1,sum(Col2),sum(Col3),sum(Col4) group by Col1 order by sum(Col4) desc label Col1 \'País\',sum(Col2) \'Receita líquida\',sum(Col3) \'Gastos\',sum(Col4) \'Lucro líquido\'",0),"Sem dados para os filtros")'
    ]],
}

partners = ['TODOS'] + sorted(set(partner_by_start.values()))
statuses = ['TODOS', 'ATIVO', 'INATIVO']
gestores = ['TODOS'] + sorted(set(row[6] for row in base_rows[1:] if row[2] == 'SITE'))
verticals = ['TODOS'] + sorted(set(row[10] for row in base_rows[1:] if row[2] == 'SITE'))
sites_list = ['TODOS'] + sorted(set(row[5] for row in base_rows[1:] if row[2] == 'SITE'))

created_at = datetime.now(timezone.utc).isoformat()
backup = {
    'created_at': created_at,
    'spreadsheet_id': SHEET_ID,
    'metadata': metadata,
    'source_ranges': {'Agosto 2026': source_range, 'CAIXA SINTETICO': caixa_range},
    'source_formula_hashes': {
        'Agosto 2026': source_formula_hash(source['formula']),
        'CAIXA SINTETICO': source_formula_hash(caixa['formula']),
    },
    'Agosto 2026': source,
    'CAIXA SINTETICO': caixa,
    'rollback': 'Delete only the newly created BASE_DASH and DASH EXECUTIVO sheet IDs recorded by the build result.',
}
backup_path = WORK / 'dashboard-august-prebuild-backup.json'
backup_sha = write_json(backup_path, backup)
candidate = {
    'created_at': created_at,
    'spreadsheet_id': SHEET_ID,
    'target_tabs': sorted(TARGET_TABS),
    'base_headers': headers,
    'base_rows': base_rows,
    'base_row_count': len(base_rows),
    'site_segment_count': sum(1 for row in base_rows[1:] if row[2] == 'SITE'),
    'country_row_count': sum(1 for row in base_rows[1:] if row[2] == 'PAÍS'),
    'daily_global_count': sum(1 for row in base_rows[1:] if row[2] == 'GERAL'),
    'monthly_closure_count': sum(1 for row in base_rows[1:] if row[2] == 'GERAL_MÊS'),
    'dashboard_values': dashboard_values,
    'filters': {'partners': partners, 'statuses': statuses, 'gestores': gestores, 'verticals': verticals, 'sites': sites_list},
    'source_formula_hashes': backup['source_formula_hashes'],
}
candidate_path = WORK / 'dashboard-august-build-candidate.json'
candidate_sha = write_json(candidate_path, candidate)
print(json.dumps({
    'status': 'pass',
    'backup_path': str(backup_path), 'backup_sha256': backup_sha,
    'candidate_path': str(candidate_path), 'candidate_sha256': candidate_sha,
    'existing_sheet_count': len(sheets), 'target_tabs_absent': True,
    'source_errors': 0,
    'base_rows': len(base_rows),
    'site_segments': candidate['site_segment_count'],
    'country_rows': candidate['country_row_count'],
    'daily_rows': candidate['daily_global_count'],
    'monthly_rows': candidate['monthly_closure_count'],
    'filters': {k: len(v) for k, v in candidate['filters'].items()},
}, ensure_ascii=False, separators=(',', ':')))
