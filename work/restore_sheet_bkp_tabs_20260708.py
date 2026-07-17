#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import csv, html, json, re, unicodedata, urllib.parse, urllib.request, urllib.error
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path('/root/mgs-agent')
SHEET_ID = '1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
SOURCE_REPORT = BASE / 'reports/dtr-sb-id-audit-sheet-update-20260706-205114.json'
TOKEN_FILE = BASE / '.secrets/ares-google-drive-oauth-client.json'
OUTDIR = BASE / 'work/sheet-bkp-restore-20260708'
OUTDIR.mkdir(parents=True, exist_ok=True)

TARGET_TABS = {
    'LOGIN_DIVERGE': 'Login difere ou vazio BKP',
    'PAGE_ID_DIVERGE': 'FB ok PG difere BKP',
    'UTM_DIVERGE': 'UTM difere BKP',
    'NO_SB_MATCH': 'Não encontrado por IDs BKP',
    'OK': 'OK LOGIN PAGE FB UTM BKP',
}
HEADERS = ['Classificação','Match por','Diferenças','DTR Bot user','DTR Segurador','DTR Página','DTR PAGE_ID/PG','DTR FB_PAGE_ID','DTR Facebook URL','DTR Email página','DTR raw','UTM esperado','SB USER_LOGIN','SB Segurador','SB Página','SB PAGE_ID/PG','SB FB_PAGE_ID','SB UTM_CAMPAIGN','SB Status','SB Restricted Until','SB Company','SB Domain','SB ID','Candidate count']

def norm(v): return '' if v is None else str(v).strip()
def ne(v): return norm(v).lower()
def clean(v): return html.unescape(re.sub(r'<[^>]+>',' ',str(v or ''))).replace('\xa0',' ').strip()
def row_values(bucket, d, s=None, basis='', diffs=None, candidate_count=''):
    diffs = diffs or []
    fb = norm(d.get('fb_page_id'))
    pg = norm(d.get('page_id'))
    expected_utm = 'pg_' + pg if pg else ''
    return [bucket, basis, ', '.join(diffs), ne(d.get('bot_user')), norm(d.get('account_name')), norm(d.get('page_name')), pg, fb, f'https://facebook.com/{fb}' if fb else '', norm(d.get('page_email')), norm(d.get('raw')), expected_utm, s.get('bot_user','') if s else '', s.get('profile_name','') if s else '', s.get('page_name','') if s else '', s.get('page_id','') if s else '', s.get('fb_page_id','') if s else '', s.get('utm_campaign','') if s else '', s.get('status','') if s else '', s.get('restricted_until','') if s else '', s.get('company','') if s else '', s.get('domain','') if s else '', s.get('sb_id','') if s else '', candidate_count]

def classify(dtr_pages, sb_rows):
    sb = sb_rows
    by_fb = defaultdict(list); by_pg = defaultdict(list)
    for s in sb:
        if s.get('fb_page_id'): by_fb[s['fb_page_id']].append(s)
        if s.get('page_id'): by_pg[s['page_id']].append(s)
    buckets = {k: [] for k in TARGET_TABS}
    matched_ids = set(); issues = []
    for d in dtr_pages:
        du = ne(d.get('bot_user')); dfb = norm(d.get('fb_page_id')); dpg = norm(d.get('page_id')); expected_utm = 'pg_' + dpg if dpg else ''
        candidates = []; basis = ''
        if dfb and by_fb.get(dfb): candidates = by_fb[dfb]; basis = 'global+FB_PAGE_ID'
        elif dpg and by_pg.get(dpg): candidates = by_pg[dpg]; basis = 'global+PAGE_ID'
        if len(candidates) == 1:
            s = candidates[0]; matched_ids.add(s.get('sb_id','')); diffs=[]
            if du != ne(s.get('bot_user')): diffs.append('USER_LOGIN')
            if dpg != norm(s.get('page_id')): diffs.append('PAGE_ID')
            if dfb != norm(s.get('fb_page_id')): diffs.append('FB_PAGE_ID')
            if expected_utm and norm(s.get('utm_campaign')) != expected_utm: diffs.append('UTM_CAMPAIGN')
            if not diffs:
                buckets['OK'].append(row_values('OK: LOGIN + PAGE_ID + FB_PAGE_ID + UTM', d, s, basis, diffs))
            else:
                if 'USER_LOGIN' in diffs: buckets['LOGIN_DIVERGE'].append(row_values('LOGIN/USER_LOGIN divergente', d, s, basis, diffs))
                if 'PAGE_ID' in diffs or 'FB_PAGE_ID' in diffs: buckets['PAGE_ID_DIVERGE'].append(row_values('PAGE_ID/FB_PAGE_ID divergente', d, s, basis, diffs))
                if 'UTM_CAMPAIGN' in diffs: buckets['UTM_DIVERGE'].append(row_values('UTM_CAMPAIGN divergente', d, s, basis, diffs))
                issues.append({'type':'DIVERGENTE','diffs':diffs})
        elif len(candidates) > 1:
            buckets['PAGE_ID_DIVERGE'].append(row_values('Ambíguo na SB por ID', d, candidates[0], basis, ['multiple_candidates'], str(len(candidates))))
        else:
            buckets['NO_SB_MATCH'].append(row_values('Não encontrado na SB por FB_PAGE_ID nem PAGE_ID', d, None, 'none_full_sb', ['missing_in_sb_after_full_global_check']))
    return buckets

def access_token():
    creds = json.loads(TOKEN_FILE.read_text())
    body = urllib.parse.urlencode({'client_id':creds['client_id'],'client_secret':creds['client_secret'],'refresh_token':creds['refresh_token'],'grant_type':'refresh_token'}).encode()
    with urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=body),timeout=30) as resp:
        return json.load(resp)['access_token']

ACCESS = None
def api(method, url, data=None, timeout=180):
    body=None; headers={'Authorization':'Bearer '+ACCESS}
    if data is not None:
        body=json.dumps(data).encode(); headers['Content-Type']='application/json; charset=UTF-8'
    req=urllib.request.Request(url,method=method,headers=headers,data=body)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            raw=resp.read(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw=exc.read().decode(errors='ignore')
        raise RuntimeError(f'HTTP {exc.code}: {raw[:1200]}') from exc

def q(title): return urllib.parse.quote(title, safe='')

def unique_title(desired, existing):
    if desired not in existing: return desired
    n=2
    while f'{desired} {n}' in existing: n+=1
    return f'{desired} {n}'

def write_values(title, sheet_id, values):
    chunk=4000; row=1
    for i in range(0,len(values),chunk):
        part=values[i:i+chunk]
        api('PUT', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{q(title)}!A{row}?valueInputOption=RAW', {'majorDimension':'ROWS','values':part}, timeout=240)
        row += len(part)
    width=len(values[0]) if values else 1
    requests=[
        {'updateSheetProperties':{'properties':{'sheetId':sheet_id,'gridProperties':{'frozenRowCount':1}},'fields':'gridProperties.frozenRowCount'}},
        {'setBasicFilter':{'filter':{'range':{'sheetId':sheet_id,'startRowIndex':0,'endRowIndex':max(1,len(values)),'startColumnIndex':0,'endColumnIndex':width}}}},
        {'repeatCell':{'range':{'sheetId':sheet_id,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':width},'cell':{'userEnteredFormat':{'textFormat':{'bold':True,'foregroundColor':{'red':1,'green':1,'blue':1}},'backgroundColor':{'red':0.12,'green':0.31,'blue':0.47}}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
        {'autoResizeDimensions':{'dimensions':{'sheetId':sheet_id,'dimension':'COLUMNS','startIndex':0,'endIndex':min(width,24)}}},
    ]
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests':requests}, timeout=180)
    rb=api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{q(title)}!A:A?majorDimension=COLUMNS')
    return max(0, len(rb.get('values',[[]])[0]) - 1)

def main():
    global ACCESS
    source = json.loads(SOURCE_REPORT.read_text())
    dtr_pages=[]
    for scan in source.get('dtr_scans',[]): dtr_pages.extend(scan.get('pages') or [])
    buckets = classify(dtr_pages, source.get('sb_rows') or [])
    # local TSV backup of what we are restoring
    for bucket,title in TARGET_TABS.items():
        with (OUTDIR / (title.replace('/','-') + '.tsv')).open('w', encoding='utf-8', newline='') as f:
            w=csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerows([HEADERS]+buckets[bucket])
    ACCESS = access_token()
    meta=api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
    existing={s['properties']['title'] for s in meta.get('sheets',[])}
    results=[]
    for bucket,desired in TARGET_TABS.items():
        title=unique_title(desired, existing); existing.add(title)
        add=api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests':[{'addSheet':{'properties':{'title':title}}}]})
        sheet_id=add['replies'][0]['addSheet']['properties']['sheetId']
        values=[HEADERS]+buckets[bucket]
        readback=write_values(title, sheet_id, values)
        expected=len(buckets[bucket])
        if readback != expected:
            raise RuntimeError(f'readback mismatch {title}: expected {expected}, got {readback}')
        results.append({'bucket':bucket,'title':title,'gid':sheet_id,'expected_rows':expected,'readback_rows':readback,'url':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={sheet_id}#gid={sheet_id}'})
    out={'source_report':str(SOURCE_REPORT),'created_tabs':results}
    (OUTDIR/'restore-results.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
