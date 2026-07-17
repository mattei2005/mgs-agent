#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json, pathlib, urllib.parse, urllib.request, urllib.error, re, time, datetime, collections, sys

TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
OUT = pathlib.Path('/root/mgs-agent/work/finance-month-rollover-audit')
OUT.mkdir(parents=True, exist_ok=True)

SHEETS = {
    'principal_2026': '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak',
    'kelly': '1huhZFlFVEKmY11fR5DxgCWE2TNC3gvw_eXlW2jylVfs',
    'isliago': '1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c',
    'george': '1cFPIlC2NxRG6GQiF4VmbNqRz09ZWkZXWUzP7nINK9vU',
    'nicolas': '128fEDdXayhgGGKMdLPf-FTWyJRW8-v6JgHzmUSrsOMU',
    'joe': '1syOKCRi-2wpHQNY5fHMcOzjj73EXmFIUbTF1sTIARvQ',
}

MONTHS = ['Janeiro','Fevereiro','Marco','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
MONTH_RE = re.compile(r'^(?:' + '|'.join(MONTHS) + r') 20\d\d$', re.I)
A1_RE = re.compile(r"(?:'([^']+)'|([A-Za-z_][\w .-]*))?!?\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?")
IMP_RE = re.compile(r'IMPORTRANGE\s*\(\s*"([^"]+)"\s*[;,]\s*"?([^"\)]*)', re.I)
FUNC_RE = re.compile(r'([A-Z][A-Z0-9_.]*)\s*\(', re.I)

# Hard safety cap only to prevent accidental monster tabs. Current finance sheets are below this.
MAX_ROWS = 2500
MAX_COLS = 900

def col(n:int)->str:
    out=''
    while n:
        n -= 1
        out = chr(65+n%26) + out
        n //= 26
    return out

def token():
    c = json.loads(TOKEN_FILE.read_text())
    body = urllib.parse.urlencode({
        'client_id': c['client_id'],
        'client_secret': c['client_secret'],
        'refresh_token': c['refresh_token'],
        'grant_type': 'refresh_token',
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['access_token']

ACCESS = token()

def api(url):
    last = None
    for attempt in range(6):
        req = urllib.request.Request(url, headers={'Authorization':'Bearer '+ACCESS})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors='ignore')[:1200]
            last = f'HTTP {e.code}: {raw}'
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(20 * (attempt+1))
                continue
            raise RuntimeError(last)
    raise RuntimeError(last or 'unknown api error')

def q(s):
    return urllib.parse.quote(s, safe='')

def normalize_external_id(s):
    m = re.search(r'/d/([A-Za-z0-9_-]+)', s)
    if m:
        return m.group(1)
    if re.fullmatch(r'[A-Za-z0-9_-]{20,}', s):
        return s
    return s

def classify_formula(f):
    u = f.upper()
    cats = []
    functions = [x.upper() for x in FUNC_RE.findall(f)]
    for key in ['IMPORTRANGE','QUERY','FILTER','VLOOKUP','XLOOKUP','INDEX','MATCH','SUMIFS','SUMIF','SUM','IFERROR','IF','DATE','MONTH','EOMONTH','DAY','TODAY','SHEETNAME','ARRAYFORMULA']:
        if key in functions or key in u:
            cats.append(key)
    if re.search(r'(?<![A-Z])\$?A\$?3(?!\d)', u): cats.append('USES_A3_MONTH_NUMBER')
    if re.search(r'(?<![A-Z])\$?B\$?4(?!\d)', u): cats.append('USES_B4_YEAR')
    if 'CAIXA SINTETICO' in u: cats.append('CAIXA_SINTETICO')
    for m in MONTHS:
        if m.upper() in u:
            cats.append('LITERAL_MONTH_NAME')
            break
    if re.search(r'!\$?H\$?\d+', u): cats.append('EXTERNAL_REF_COL_H')
    if re.search(r'!\$?I\$?\d+', u): cats.append('EXTERNAL_REF_COL_I')
    return sorted(set(cats)) or ['OTHER']

def extract_refs(f):
    out=[]
    for m in IMP_RE.finditer(f):
        out.append({'type':'importrange', 'spreadsheet': normalize_external_id(m.group(1)), 'range': m.group(2)[:120]})
    # lightweight local refs; filtered to avoid every function token
    for m in re.finditer(r"(?:'([^']+)'|([A-Za-z][A-Za-z0-9_ .-]{0,50}))!\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?", f):
        sheet = m.group(1) or m.group(2)
        out.append({'type':'sheet_ref', 'sheet': sheet[:80], 'ref': m.group(0)[:120]})
    return out[:20]

def maybe_area(cell, formula, tab_title):
    u = formula.upper()
    if 'IMPORTRANGE' in u: return 'importa outra planilha/aba'
    if 'CAIXA SINTETICO' in u: return 'resumo/caixa sintético'
    if '$A$3' in u or 'DATE($B$4,$A$3' in u: return 'cálculo dependente do mês da aba'
    if any(x in u for x in ['SUMIF','SUMIFS']): return 'somatório condicional'
    if any(x in u for x in ['EOMONTH','DAY(']): return 'distribuição por dias do mês'
    if any(x in u for x in ['VLOOKUP','XLOOKUP','INDEX','MATCH']): return 'busca/mapeamento'
    if any(x in u for x in ['FILTER','QUERY']): return 'filtro/consulta'
    return 'fórmula local'

def main():
    started = datetime.datetime.now().isoformat(timespec='seconds')
    full = {'started': started, 'sheets': {}}
    exec_rows = []
    for name, sid in SHEETS.items():
        meta = api(f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=properties(title),sheets(properties(sheetId,title,index,gridProperties(rowCount,columnCount)))')
        props = meta['properties']
        tabs = [s['properties'] for s in meta.get('sheets', [])]
        ranges=[]; tab_meta={}
        for p in tabs:
            rows = min(int(p.get('gridProperties',{}).get('rowCount', 1000) or 1000), MAX_ROWS)
            cols = min(int(p.get('gridProperties',{}).get('columnCount', 26) or 26), MAX_COLS)
            tab_meta[p['title']] = {'sheetId': p['sheetId'], 'rows_scanned': rows, 'cols_scanned': cols, 'is_month_tab': bool(MONTH_RE.match(p['title']))}
            ranges.append(f"'{p['title']}'!A1:{col(cols)}{rows}")
        params = urllib.parse.urlencode([('ranges', r) for r in ranges] + [('valueRenderOption','FORMULA')])
        batch = api(f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchGet?{params}')
        sheet_report = {
            'title': props.get('title'), 'spreadsheet_id': sid, 'tabs_scanned': len(tabs),
            'formula_count': 0, 'error_like_values': collections.Counter(), 'function_counts': collections.Counter(),
            'category_counts': collections.Counter(), 'external_spreadsheets': collections.Counter(),
            'month_tab_summary': {}, 'critical_formulas': [], 'formula_groups': collections.defaultdict(list),
        }
        for vr in batch.get('valueRanges', []):
            rng = vr.get('range','')
            m = re.match(r"'?(.+?)'?!", rng)
            title = (m.group(1).replace("''", "'") if m else rng)
            vals = vr.get('values', [])
            t = {'formula_count':0, 'category_counts':collections.Counter(), 'areas':collections.Counter(), 'sample_by_area':collections.defaultdict(list), 'errors':collections.Counter()}
            for r, row in enumerate(vals, 1):
                for c, v in enumerate(row, 1):
                    if not isinstance(v, str):
                        continue
                    cell = f'{col(c)}{r}'
                    if v.startswith('='):
                        cats = classify_formula(v)
                        area = maybe_area(cell, v, title)
                        funcs = [x.upper() for x in FUNC_RE.findall(v)]
                        t['formula_count'] += 1
                        sheet_report['formula_count'] += 1
                        t['areas'][area] += 1
                        for cat in cats:
                            t['category_counts'][cat] += 1
                            sheet_report['category_counts'][cat] += 1
                        for fn in funcs:
                            sheet_report['function_counts'][fn] += 1
                        refs = extract_refs(v)
                        for ref in refs:
                            if ref['type'] == 'importrange':
                                sheet_report['external_spreadsheets'][ref['spreadsheet']] += 1
                        item = {'tab': title, 'cell': cell, 'formula': v, 'categories': cats, 'area': area, 'refs': refs}
                        if len(t['sample_by_area'][area]) < 8:
                            t['sample_by_area'][area].append(item)
                        if any(x in cats for x in ['USES_A3_MONTH_NUMBER','USES_B4_YEAR','CAIXA_SINTETICO','EXTERNAL_REF_COL_H','EXTERNAL_REF_COL_I','LITERAL_MONTH_NAME']):
                            if len(sheet_report['critical_formulas']) < 300:
                                sheet_report['critical_formulas'].append(item)
                        # Keep compact grouped representative formulas for understanding, not every formula.
                        key = '|'.join(cats[:4])
                        if len(sheet_report['formula_groups'][key]) < 10:
                            sheet_report['formula_groups'][key].append(item)
                    elif v.startswith('#'):
                        t['errors'][v] += 1
                        sheet_report['error_like_values'][v] += 1
            t['category_counts'] = dict(t['category_counts'])
            t['areas'] = dict(t['areas'])
            t['errors'] = dict(t['errors'])
            t['sample_by_area'] = {k:v for k,v in t['sample_by_area'].items()}
            sheet_report['month_tab_summary'][title] = t
        # convert counters/defaultdicts
        sheet_report['function_counts'] = dict(sheet_report['function_counts'].most_common())
        sheet_report['category_counts'] = dict(sheet_report['category_counts'].most_common())
        sheet_report['external_spreadsheets'] = dict(sheet_report['external_spreadsheets'].most_common())
        sheet_report['error_like_values'] = dict(sheet_report['error_like_values'])
        sheet_report['formula_groups'] = dict(sheet_report['formula_groups'])
        full['sheets'][name] = sheet_report
        exec_rows.append({
            'key': name,
            'title': sheet_report['title'],
            'formulas': sheet_report['formula_count'],
            'importrange': sheet_report['category_counts'].get('IMPORTRANGE',0),
            'uses_a3': sheet_report['category_counts'].get('USES_A3_MONTH_NUMBER',0),
            'caixa': sheet_report['category_counts'].get('CAIXA_SINTETICO',0),
            'literal_month': sheet_report['category_counts'].get('LITERAL_MONTH_NAME',0),
            'errors': sum(sheet_report['error_like_values'].values()),
            'top_external': list(sheet_report['external_spreadsheets'].items())[:5],
        })
    full['executive_summary'] = exec_rows
    full['finished'] = datetime.datetime.now().isoformat(timespec='seconds')
    out_json = OUT / f'full-formula-understanding-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
    out_json.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding='utf-8')
    # concise markdown report
    md = []
    md.append('# Auditoria completa de fórmulas — virada mensal financeira')
    md.append(f'Gerado em: {full["finished"]}')
    md.append('')
    md.append('## Resumo por planilha')
    md.append('')
    md.append('| Planilha | Fórmulas | IMPORTRANGE | Usa A3 | Caixa | Mês literal | Erros |')
    md.append('|---|---:|---:|---:|---:|---:|---:|')
    for r in exec_rows:
        md.append(f"| {r['key']} | {r['formulas']} | {r['importrange']} | {r['uses_a3']} | {r['caixa']} | {r['literal_month']} | {r['errors']} |")
    md.append('')
    md.append('## Interligações externas mais importantes')
    for r in exec_rows:
        md.append(f"\n### {r['key']} — {r['title']}")
        for ext, cnt in r['top_external']:
            md.append(f'- {ext}: {cnt} referências')
    md.append('')
    md.append('## Fórmulas críticas representativas')
    for name, sr in full['sheets'].items():
        md.append(f"\n### {name}")
        for item in sr['critical_formulas'][:20]:
            formula = item['formula'].replace('\n',' ')[:240]
            md.append(f"- {item['tab']}!{item['cell']} — {item['area']} — `{formula}`")
    out_md = OUT / f'full-formula-understanding-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
    out_md.write_text('\n'.join(md), encoding='utf-8')
    print(json.dumps({'ok': True, 'json': str(out_json), 'md': str(out_md), 'summary': exec_rows}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
