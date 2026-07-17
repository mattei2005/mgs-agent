#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json, pathlib, urllib.parse, urllib.request, urllib.error, re, time, datetime, collections, gzip, hashlib

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
ID_TO_KEY = {v:k for k,v in SHEETS.items()}
HISTORICAL_ID = '1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso'
MONTH_NAMES = ['Janeiro','Fevereiro','Marco','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
MONTH_RE = re.compile(r'^(?:' + '|'.join(MONTH_NAMES) + r') 20\d\d$', re.I)
FUNC_RE = re.compile(r'([A-Z][A-Z0-9_.]*)\s*\(', re.I)
IMP_RE = re.compile(r'IMPORTRANGE\s*\(\s*"([^"]+)"\s*[;,]\s*(?:"([^"]*)"|([^\)]*))', re.I)
LOCAL_REF_RE = re.compile(r"(?:'([^']+)'|([A-Za-z][A-Za-z0-9_ .-]{0,60}))!\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?")
MAX_ROWS = 2500
MAX_COLS = 900


def col(n:int)->str:
    out=''
    while n:
        n -= 1
        out = chr(65+n%26) + out
        n //= 26
    return out

def cell_to_rc(a1):
    m = re.match(r'([A-Z]+)(\d+)', a1)
    if not m: return None
    c = 0
    for ch in m.group(1): c = c*26 + (ord(ch)-64)
    return int(m.group(2)), c

def normalize_formula(f):
    # Keep structure while collapsing row-specific repetitions and quoted spreadsheet IDs.
    s = f.upper()
    s = re.sub(r'"(?:HTTPS://DOCS\.GOOGLE\.COM/SPREADSHEETS/D/)?[A-Z0-9_-]{20,}(?:/EDIT)?"', '"<SPREADSHEET_ID>"', s)
    s = re.sub(r'\$?[A-Z]{1,3}\$?\d+', '<CELL>', s)
    s = re.sub(r'ROW\(\)-\d+', 'ROW()-N', s)
    s = re.sub(r'\d+(?:\.\d+)?', '<NUM>', s)
    return s

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
    for attempt in range(8):
        req = urllib.request.Request(url, headers={'Authorization':'Bearer '+ACCESS})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors='ignore')[:1000]
            last = f'HTTP {e.code}: {raw}'
            if e.code in (429, 500, 502, 503, 504) and attempt < 7:
                time.sleep(min(90, 15 * (attempt + 1)))
                continue
            raise RuntimeError(last)
    raise RuntimeError(last or 'unknown api error')

def q(s): return urllib.parse.quote(s, safe='')

def norm_id(x):
    m = re.search(r'/d/([A-Za-z0-9_-]+)', x or '')
    if m: return m.group(1)
    if re.fullmatch(r'[A-Za-z0-9_-]{20,}', x or ''): return x
    return x or ''

def classify(f):
    u=f.upper(); funcs=[x.upper() for x in FUNC_RE.findall(f)]
    cats=[]
    for key in ['IMPORTRANGE','QUERY','FILTER','VLOOKUP','XLOOKUP','INDEX','MATCH','SUMIFS','SUMIF','SUM','IFERROR','IF','DATE','MONTH','EOMONTH','DAY','TODAY','SHEETNAME','ARRAYFORMULA']:
        if key in funcs or key in u: cats.append(key)
    if re.search(r'(?<![A-Z])\$?A\$?3(?!\d)', u): cats.append('USES_A3_MONTH_NUMBER')
    if re.search(r'(?<![A-Z])\$?B\$?4(?!\d)', u): cats.append('USES_B4_YEAR')
    if 'CAIXA SINTETICO' in u: cats.append('CAIXA_SINTETICO')
    if 'SHEETNAME()' in u: cats.append('TAB_NAME_DEPENDENT')
    if any(m.upper() in u for m in MONTH_NAMES): cats.append('LITERAL_MONTH_NAME')
    if re.search(r'!\$?H\$?\d+', u): cats.append('EXTERNAL_REF_COL_H')
    if re.search(r'!\$?I\$?\d+', u): cats.append('EXTERNAL_REF_COL_I')
    return sorted(set(cats)) or ['OTHER']

def role_from_position(tab, cell, formula, labels):
    r,c = cell_to_rc(cell) or (0,0)
    u = formula.upper()
    left = labels.get((r,c-1),'')
    above = labels.get((r-1,c),'')
    nearby = ' '.join([left, above, labels.get((r,1),''), labels.get((1,c),'')]).lower()
    if 'IMPORTRANGE' in u and 'SHEETNAME()' in u:
        return 'importa bloco mensal com nome da aba'
    if 'IMPORTRANGE' in u and 'CAIXA SINTETICO' in u:
        return 'importa caixa sintético'
    if 'IMPORTRANGE' in u:
        return 'importa outra planilha'
    if '$A$3' in u or 'DATE($B$4,$A$3' in u:
        if 'EOMONTH' in u and 'DAY' in u: return 'rateia despesa pelo número de dias do mês'
        return 'usa mês/ano da aba'
    if 'FILTER' in u and 'SITES E VERTICAIS' in u:
        return 'puxa cadastro/lista de sites e verticais'
    if any(x in nearby for x in ['despesa', 'gasto', 'spend', 'bm', 'google ads']): return 'cálculo de gasto/despesa'
    if any(x in nearby for x in ['receita', 'gross', 'revenue']): return 'cálculo de receita'
    if any(x in nearby for x in ['lucro', 'profit']): return 'cálculo de lucro'
    if any(x in nearby for x in ['margem', 'roi']): return 'cálculo de margem/roi'
    if any(x in u for x in ['SUMIF','SUMIFS']): return 'somatório condicional'
    if any(x in u for x in ['SUM(']): return 'somatório/local total'
    return 'fórmula auxiliar/local'

def extract_dependencies(formula):
    deps=[]
    for m in IMP_RE.finditer(formula):
        sid=norm_id(m.group(1)); rng=(m.group(2) or m.group(3) or '').strip()
        deps.append({'type':'external_importrange','spreadsheet_id':sid,'spreadsheet_key':ID_TO_KEY.get(sid, 'historical' if sid==HISTORICAL_ID else 'unknown'), 'range':rng[:200]})
    for m in LOCAL_REF_RE.finditer(formula):
        sheet=(m.group(1) or m.group(2) or '').strip()
        deps.append({'type':'local_or_named_sheet_ref','sheet':sheet,'ref':m.group(0)[:160]})
    return deps

def read_sheet(spreadsheet_key, sid):
    meta = api(f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=properties(title),sheets(properties(sheetId,title,index,gridProperties(rowCount,columnCount)))')
    tabs = [s['properties'] for s in meta.get('sheets', [])]
    ranges=[]
    tab_scan={}
    for p in tabs:
        rows=min(int(p.get('gridProperties',{}).get('rowCount',1000) or 1000), MAX_ROWS)
        cols=min(int(p.get('gridProperties',{}).get('columnCount',26) or 26), MAX_COLS)
        tab_scan[p['title']]={'rows':rows,'cols':cols,'sheet_id':p['sheetId']}
        ranges.append(f"'{p['title']}'!A1:{col(cols)}{rows}")
    params=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('valueRenderOption','FORMULA')])
    formula_batch=api(f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchGet?{params}')
    params2=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('valueRenderOption','FORMATTED_VALUE')])
    value_batch=api(f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchGet?{params2}')
    return meta, formula_batch, value_batch, tab_scan

def range_title(vr):
    rng=vr.get('range','')
    m=re.match(r"'?(.+?)'?!", rng)
    return (m.group(1).replace("''","'") if m else rng)

def main():
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    raw_path=OUT/f'all-formulas-{stamp}.jsonl.gz'
    summary={'started':datetime.datetime.now().isoformat(timespec='seconds'), 'sheets':{}, 'edges':[], 'global_findings':[]}
    raw_count=0
    with gzip.open(raw_path, 'wt', encoding='utf-8') as raw:
        for skey,sid in SHEETS.items():
            meta, fb, vb, tab_scan = read_sheet(skey,sid)
            values_by_tab={range_title(vr): vr.get('values',[]) for vr in vb.get('valueRanges',[])}
            sheet_sum={
                'title':meta['properties'].get('title'), 'spreadsheet_id':sid, 'tabs_scanned':tab_scan,
                'formula_count':0, 'unique_exact_formulas':0, 'unique_normalized_patterns':0,
                'tab_summaries':{}, 'category_counts':collections.Counter(), 'role_counts':collections.Counter(),
                'function_counts':collections.Counter(), 'external_links':collections.Counter(),
                'pattern_examples':{}, 'critical_cells':[], 'possible_issues':[]
            }
            exact=set(); patterns=collections.Counter(); pattern_examples={}
            for vr in fb.get('valueRanges',[]):
                tab=range_title(vr); fvals=vr.get('values',[]); vals=values_by_tab.get(tab,[])
                # map non-formula labels for nearby context
                labels={}
                for r,row in enumerate(vals,1):
                    for c,v in enumerate(row,1):
                        if isinstance(v,str) and v and not v.startswith('=') and not v.startswith('#'):
                            if len(v) <= 80: labels[(r,c)] = v
                tsum={'formula_count':0,'unique_patterns':0,'roles':collections.Counter(),'categories':collections.Counter(),'dependencies':collections.Counter(),'errors':collections.Counter(),'representatives':[]}
                tab_patterns=set()
                for r,row in enumerate(fvals,1):
                    for c,f in enumerate(row,1):
                        if not isinstance(f,str): continue
                        cell=f'{col(c)}{r}'
                        if f.startswith('='):
                            raw_count+=1; sheet_sum['formula_count']+=1; tsum['formula_count']+=1
                            exact.add(f)
                            pat=normalize_formula(f); ph=hashlib.sha1(pat.encode()).hexdigest()[:12]
                            patterns[ph]+=1; tab_patterns.add(ph)
                            cats=classify(f); role=role_from_position(tab,cell,f,labels); funcs=[x.upper() for x in FUNC_RE.findall(f)]
                            deps=extract_dependencies(f)
                            for cat in cats: sheet_sum['category_counts'][cat]+=1; tsum['categories'][cat]+=1
                            sheet_sum['role_counts'][role]+=1; tsum['roles'][role]+=1
                            for fn in funcs: sheet_sum['function_counts'][fn]+=1
                            for d in deps:
                                if d['type']=='external_importrange':
                                    edge=(skey, d['spreadsheet_key'], d['spreadsheet_id'], d['range'])
                                    sheet_sum['external_links'][f"{d['spreadsheet_key']}:{d['range']}"] += 1
                                    summary['edges'].append({'from_sheet':skey,'from_tab':tab,'from_cell':cell, **d})
                                else:
                                    tsum['dependencies'][d.get('sheet','?')] += 1
                            item={'sheet_key':skey,'spreadsheet_title':sheet_sum['title'],'tab':tab,'cell':cell,'formula':f,'normalized_pattern_hash':ph,'categories':cats,'role':role,'dependencies':deps}
                            raw.write(json.dumps(item,ensure_ascii=False)+'\n')
                            if ph not in pattern_examples:
                                pattern_examples[ph]={'count':0,'normalized':pat[:500], 'examples':[]}
                            pattern_examples[ph]['count']+=1
                            if len(pattern_examples[ph]['examples'])<5:
                                pattern_examples[ph]['examples'].append({'tab':tab,'cell':cell,'formula':f[:500],'role':role,'categories':cats})
                            critical = any(x in cats for x in ['USES_A3_MONTH_NUMBER','USES_B4_YEAR','CAIXA_SINTETICO','TAB_NAME_DEPENDENT','LITERAL_MONTH_NAME','EXTERNAL_REF_COL_H','EXTERNAL_REF_COL_I'])
                            if critical and len(sheet_sum['critical_cells']) < 500:
                                sheet_sum['critical_cells'].append({'tab':tab,'cell':cell,'formula':f[:500],'role':role,'categories':cats,'dependencies':deps[:5]})
                            if 'LITERAL_MONTH_NAME' in cats and MONTH_RE.match(tab or '') and tab.split()[0].upper() not in f.upper():
                                if len(sheet_sum['possible_issues']) < 100:
                                    sheet_sum['possible_issues'].append({'type':'month_literal_not_matching_tab','tab':tab,'cell':cell,'formula':f[:400]})
                        elif f.startswith('#'):
                            tsum['errors'][f]+=1
                tsum['unique_patterns']=len(tab_patterns)
                tsum['roles']=dict(tsum['roles'].most_common())
                tsum['categories']=dict(tsum['categories'].most_common())
                tsum['dependencies']=dict(tsum['dependencies'].most_common())
                tsum['errors']=dict(tsum['errors'])
                sheet_sum['tab_summaries'][tab]=tsum
            sheet_sum['unique_exact_formulas']=len(exact)
            sheet_sum['unique_normalized_patterns']=len(patterns)
            sheet_sum['category_counts']=dict(sheet_sum['category_counts'].most_common())
            sheet_sum['role_counts']=dict(sheet_sum['role_counts'].most_common())
            sheet_sum['function_counts']=dict(sheet_sum['function_counts'].most_common())
            sheet_sum['external_links']=dict(sheet_sum['external_links'].most_common())
            top_patterns=patterns.most_common(80)
            sheet_sum['pattern_examples']={h:pattern_examples[h] for h,_ in top_patterns}
            summary['sheets'][skey]=sheet_sum
    # aggregate edges
    edge_counts=collections.Counter()
    for e in summary['edges']:
        edge_counts[(e['from_sheet'],e['spreadsheet_key'],e.get('spreadsheet_id',''))]+=1
    summary['edge_counts']=[{'from':a,'to':b,'to_id':c,'count':n} for (a,b,c),n in edge_counts.most_common()]
    summary['raw_formula_index_gzip']=str(raw_path)
    summary['raw_formula_count']=raw_count
    summary['finished']=datetime.datetime.now().isoformat(timespec='seconds')
    json_path=OUT/f'deep-dependency-summary-{stamp}.json'
    json_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    # create concise operational md
    md=[]
    md.append('# Mapa de fórmulas e dependências — financeiro MGS')
    md.append(f'Gerado em: {summary["finished"]}')
    md.append(f'Fórmulas indexadas: {raw_count}')
    md.append('')
    md.append('## Resumo estrutural')
    md.append('| Planilha | Fórmulas | Fórmulas únicas | Padrões únicos | IMPORTRANGE | A3/mês | Caixa | Erros |')
    md.append('|---|---:|---:|---:|---:|---:|---:|---:|')
    for skey,s in summary['sheets'].items():
        err=sum(sum(ts.get('errors',{}).values()) for ts in s['tab_summaries'].values())
        md.append(f"| {skey} | {s['formula_count']} | {s['unique_exact_formulas']} | {s['unique_normalized_patterns']} | {s['category_counts'].get('IMPORTRANGE',0)} | {s['category_counts'].get('USES_A3_MONTH_NUMBER',0)} | {s['category_counts'].get('CAIXA_SINTETICO',0)} | {err} |")
    md.append('\n## Interligações')
    for e in summary['edge_counts']:
        md.append(f"- {e['from']} → {e['to']} ({e['count']} fórmulas)")
    md.append('\n## Funções por área — top roles')
    for skey,s in summary['sheets'].items():
        md.append(f"\n### {skey} — {s['title']}")
        for role,cnt in list(s['role_counts'].items())[:12]:
            md.append(f'- {role}: {cnt}')
    md.append('\n## Pontos críticos para virada Junho→Julho')
    md.append('- Principal usa A3 como número do mês em milhares de fórmulas de distribuição diária; mudar 6→7 é obrigatório.')
    md.append('- Principal usa B4 como ano junto com A3; confirmar 2026.')
    md.append('- Todas as abas de gestores dependem de paridade exata do nome da aba via SHEETNAME()/IMPORTRANGE.')
    md.append('- CAIXA SINTETICO precisa avançar da coluna de junho para a coluna de julho.')
    md.append('- Coluna B/datas do mês precisa ser reconstruída para 31 dias de julho.')
    md.append('\n## Possíveis inconsistências detectadas')
    any_issue=False
    for skey,s in summary['sheets'].items():
        if s['possible_issues']:
            any_issue=True
            md.append(f"\n### {skey}")
            for issue in s['possible_issues'][:20]:
                md.append(f"- {issue['type']} em {issue['tab']}!{issue['cell']}: `{issue['formula'][:180]}`")
    if not any_issue:
        md.append('- Nenhuma inconsistência automática de fórmula/erro visível encontrada nesta leitura.')
    md_path=OUT/f'deep-dependency-report-{stamp}.md'
    md_path.write_text('\n'.join(md),encoding='utf-8')
    print(json.dumps({'ok':True,'summary_json':str(json_path),'report_md':str(md_path),'raw_formula_index_gzip':str(raw_path),'formula_count':raw_count,'edge_counts':summary['edge_counts'][:20]},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
