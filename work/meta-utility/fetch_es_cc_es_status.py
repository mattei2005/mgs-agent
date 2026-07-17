#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import asyncio, csv, datetime, json, pathlib, re, urllib.parse, urllib.request, urllib.error
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

TARGET_TEMPLATE = 'teste-5-es-cc-es-all-201-zero-width-2chars-approval'
SHEET_ID = '1ieSjYbhl34T0tWOvvol3F2lhvCoVTWHm9_YnUkoVhtM'
SHEET_TAB = 'ES-CC-ES'
SUMMARY_TAB = 'ES-CC-ES Approval Summary'
WORK = pathlib.Path('/root/mgs-agent/work/meta-utility/es-cc-es-translation-20260630')
TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
RAW_OUT = WORK / 'es-cc-es-test5-broadcast-raw.json'
CSV_OUT = WORK / 'es-cc-es-test5-status-from-dash.csv'
AUDIT_OUT = WORK / 'es-cc-es-test5-status-sheet-update-audit.json'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
ZW_RE = re.compile('[\u200b\u200c\u200d\ufeff\u2060]')

def visible(s):
    return ZW_RE.sub('', s or '')

def status_of(m):
    vals = {k:int(m.get(k) or 0) for k in ('APPROVED','INVALID_FORMAT','REJECTED','ERROR')}
    # Prefer the terminal/negative states if present; otherwise APPROVED.
    if vals['INVALID_FORMAT'] > 0: return 'INVALID_FORMAT'
    if vals['REJECTED'] > 0: return 'REJECTED'
    if vals['ERROR'] > 0: return 'ERROR'
    if vals['APPROVED'] > 0: return 'APPROVED'
    return ''

def access_token():
    creds = json.loads(TOKEN_FILE.read_text())
    body = urllib.parse.urlencode({
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'],
        'refresh_token': creds['refresh_token'],
        'grant_type': 'refresh_token',
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['access_token']

def gapi(token, method, url, data=None):
    headers={'Authorization':'Bearer '+token}
    body=None
    if data is not None:
        body=json.dumps(data).encode(); headers['Content-Type']='application/json; charset=UTF-8'
    req=urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw=r.read(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Google API HTTP {e.code}: {e.read().decode(errors="ignore")[:500]}')

async def fetch_broadcast_rows():
    captured=[]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json', viewport={'width':1600,'height':1000}, user_agent=UA)
        page = await ctx.new_page()
        async def on_response(resp):
            url = resp.url.lower()
            if '/broadcast/messenger' in url and resp.status == 200:
                try:
                    data = await resp.json()
                    if isinstance(data, list):
                        captured.append({'url': resp.url, 'rows': data})
                except Exception:
                    pass
        page.on('response', on_response)
        await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='networkidle', timeout=90000)
        await page.wait_for_timeout(2500)
        body = await page.locator('body').inner_text(timeout=10000)
        if 'Accounts' not in body and 'Broadcast Template' not in body:
            raise RuntimeError('SB accounts did not load: '+re.sub(r'\s+',' ',body)[:500])
        # Explicit Messenger context + Broadcast Template tab to trigger the app API with its runtime auth.
        try:
            await page.locator('.p-dropdown').first.click(timeout=10000)
            await page.wait_for_timeout(500)
            await page.get_by_text('Messenger', exact=True).last.click(timeout=10000)
            await page.wait_for_timeout(2500)
        except Exception:
            pass
        await page.get_by_text('Broadcast Template', exact=True).click(timeout=15000)
        await page.wait_for_timeout(7000)
        await browser.close()
    rows=[]
    for c in captured:
        for r in c['rows']:
            if isinstance(r, dict): rows.append(r)
    # dedupe by ID, preserving latest occurrence
    dedup={}
    for r in rows:
        dedup[r.get('ID') or r.get('id') or r.get('NAME')]=r
    return list(dedup.values())

def parse_messages(row):
    msg = row.get('MESSAGES') or row.get('messages') or '[]'
    if isinstance(msg, str):
        return json.loads(msg)
    return msg

def update_sheet(messages, row):
    token=access_token()
    # backup current ES tab
    now = datetime.datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d-%H%M%S')
    backup = WORK / f'es-cc-es-before-test5-status-update-{now}.json'
    current = gapi(token, 'GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SHEET_TAB)}!A:Z')
    backup.write_text(json.dumps(current, ensure_ascii=False, indent=2))
    vals=current.get('values', [])
    if not vals:
        raise RuntimeError(f'Sheet tab {SHEET_TAB} is empty')
    header=vals[0]
    if 'MESSAGE ID' not in header:
        raise RuntimeError('MESSAGE ID column not found in ES-CC-ES')
    if 'STATUS' not in header:
        header = header + ['STATUS']
    status_idx = header.index('STATUS')
    id_idx = header.index('MESSAGE ID')
    status_by_id={str(m.get('MESSAGE_ID') or m.get('MESSAGE ID')): status_of(m) for m in messages}
    out=[header]
    for line in vals[1:]:
        new=list(line)
        if len(new)<len(header): new += ['']*(len(header)-len(new))
        mid = str(new[id_idx]).strip()
        if mid in status_by_id:
            new[status_idx] = status_by_id[mid]
        out.append(new)
    # write ES tab back with STATUS column
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SHEET_TAB)}!A:Z:clear',{})
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate',{
        'valueInputOption':'RAW',
        'data':[{'range': f"'{SHEET_TAB}'!A1", 'majorDimension':'ROWS', 'values': out}]
    })
    counts={}
    for s in status_by_id.values(): counts[s]=counts.get(s,0)+1
    summary=[
        ['Template', TARGET_TEMPLATE],
        ['Template ID', row.get('ID','')],
        ['Updated ET', datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')],
        ['Rows', len(messages)],
        ['APPROVED', counts.get('APPROVED',0)],
        ['REJECTED', counts.get('REJECTED',0)],
        ['INVALID_FORMAT', counts.get('INVALID_FORMAT',0)],
        ['ERROR', counts.get('ERROR',0)],
        ['Blank', counts.get('',0)],
    ]
    # ensure summary tab
    ss=gapi(token,'GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
    tabs={s['properties']['title']:s['properties']['sheetId'] for s in ss.get('sheets',[])}
    if SUMMARY_TAB not in tabs:
        gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':[{'addSheet':{'properties':{'title':SUMMARY_TAB}}}]})
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SUMMARY_TAB)}!A:Z:clear',{})
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate',{
        'valueInputOption':'RAW',
        'data':[{'range': f"'{SUMMARY_TAB}'!A1", 'majorDimension':'ROWS', 'values': summary}]
    })
    rb=gapi(token,'GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SHEET_TAB)}!A:A')
    return backup, max(0,len(rb.get('values',[]))-1), counts

async def main():
    WORK.mkdir(parents=True, exist_ok=True)
    rows = await fetch_broadcast_rows()
    RAW_OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    match = None
    for r in rows:
        if (r.get('NAME') or '').strip().lower() == TARGET_TEMPLATE.lower():
            match=r; break
    if not match:
        partial=[(r.get('ID'), r.get('NAME')) for r in rows if 'teste' in (r.get('NAME') or '').lower() or 'es-cc-es' in (r.get('NAME') or '').lower()]
        raise RuntimeError(f'Template not found. Captured rows={len(rows)} partial={partial[:30]}')
    messages=parse_messages(match)
    messages=sorted(messages, key=lambda m:int(m.get('MESSAGE_ID') or m.get('MESSAGE ID') or 0))
    with CSV_OUT.open('w', encoding='utf-8-sig', newline='') as f:
        cols=['MESSAGE ID','TEXT','CTA 1','LINK 1','STATUS','APPROVED','REJECTED','INVALID_FORMAT','ERROR']
        w=csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n'); w.writeheader()
        for m in messages:
            w.writerow({
                'MESSAGE ID': m.get('MESSAGE_ID',''),
                'TEXT': visible(m.get('TEXT','')),
                'CTA 1': m.get('CTA_1',''),
                'LINK 1': m.get('LINK_1',''),
                'STATUS': status_of(m),
                'APPROVED': m.get('APPROVED',0),
                'REJECTED': m.get('REJECTED',0),
                'INVALID_FORMAT': m.get('INVALID_FORMAT',0),
                'ERROR': m.get('ERROR',0),
            })
    backup, readback_rows, counts = update_sheet(messages, match)
    audit={
        'status':'OK',
        'executed_at_et': datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),
        'template': TARGET_TEMPLATE,
        'template_id': match.get('ID'),
        'rows': len(messages),
        'counts': counts,
        'csv': str(CSV_OUT),
        'raw': str(RAW_OUT),
        'sheet_url': f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
        'tab': SHEET_TAB,
        'summary_tab': SUMMARY_TAB,
        'readback_rows': readback_rows,
        'backup': str(backup),
        'sample': [{'id':m.get('MESSAGE_ID'), 'status':status_of(m), 'visible_text':visible(m.get('TEXT',''))[:140], 'cta':m.get('CTA_1','')} for m in messages[:8]],
    }
    AUDIT_OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps({k:audit[k] for k in ('status','template_id','rows','counts','tab','summary_tab','readback_rows','csv','audit') if k in audit}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
