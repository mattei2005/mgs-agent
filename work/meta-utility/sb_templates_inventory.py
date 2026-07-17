#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import asyncio, csv, json, pathlib, re, urllib.parse, urllib.request, datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

WORK = pathlib.Path('/root/mgs-agent/work/meta-utility')
OUT = WORK / 'sb-messenger-broadcast-templates-inventory.csv'
SHEET_ID = '1ieSjYbhl34T0tWOvvol3F2lhvCoVTWHm9_YnUkoVhtM'
TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
SHEET_TAB = 'SB Broadcast Templates'

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'

async def visible_text(locator):
    try:
        return await locator.inner_text(timeout=3000)
    except Exception:
        return ''

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(
            storage_state='/tmp/smartbidding_state_headed.json',
            viewport={'width': 1600, 'height': 1000},
            user_agent=UA,
        )
        page = await ctx.new_page()
        logs = []
        page.on('console', lambda msg: logs.append(f'{msg.type}: {msg.text[:240]}'))
        await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='networkidle', timeout=90000)
        await page.wait_for_timeout(2500)
        body = await visible_text(page.locator('body'))
        if 'Accounts' not in body:
            raise RuntimeError('Accounts page did not load: '+re.sub(r'\s+',' ',body)[:500])

        # Select Messenger context explicitly from the top source dropdown.
        # Do not trust raw body text because notifications may contain the word Messenger.
        await page.locator('.p-dropdown').first.click(timeout=10000)
        await page.wait_for_timeout(500)
        await page.get_by_text('Messenger', exact=True).last.click(timeout=10000)
        await page.wait_for_timeout(2500)

        await page.get_by_text('Broadcast Template', exact=True).click(timeout=10000)
        await page.wait_for_timeout(5000)

        # Apply COMPANY filter = digital-tr.
        filter_buttons = page.locator('button.p-column-filter-menu-button')
        for _ in range(20):
            if await filter_buttons.count() >= 1:
                break
            await page.wait_for_timeout(500)
        if await filter_buttons.count() < 1:
            debug_body = re.sub(r'\s+', ' ', await visible_text(page.locator('body')))[:1200]
            raise RuntimeError('No column filter buttons found; body='+debug_body)
        await filter_buttons.nth(0).click(timeout=10000)
        await page.wait_for_timeout(500)
        inputs = page.locator('.p-column-filter-overlay input, input.p-inputtext, input')
        typed = False
        for i in range(await inputs.count()):
            inp = inputs.nth(i)
            try:
                box = await inp.bounding_box(timeout=1000)
                if box and box['width'] > 20 and box['height'] > 10:
                    await inp.fill('digital-tr', timeout=3000)
                    typed = True
                    break
            except Exception:
                pass
        if not typed:
            raise RuntimeError('Could not type into company filter input')
        apply = page.get_by_role('button', name=re.compile('Apply', re.I))
        if await apply.count():
            await apply.first.click(timeout=5000)
        else:
            await page.keyboard.press('Enter')
        await page.wait_for_timeout(2500)

        # Extract columns and all paginated rows.
        headers = await page.evaluate(r'''() => [...document.querySelectorAll("thead th")]
            .map(th => (th.innerText || '').replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
            .filter(Boolean)
            .map(h => h.replace(/\s*(↑|↓|↕|Filter).*$/g, '').trim())
        ''')
        # Known visible columns for Messenger > Broadcast Template.
        wanted = ['COMPANY', 'DOMAIN', 'LANGUAGE', 'NAME', 'MESSAGES', 'LEADS', 'PAGES', 'APPROVAL']
        headers = [h for h in headers if h in wanted] or wanted

        rows = []
        seen_pages = 0
        while True:
            seen_pages += 1
            page_rows = await page.evaluate(r'''(headers) => {
                const trs = [...document.querySelectorAll('tbody tr')];
                return trs.map(tr => {
                    const cells = [...tr.querySelectorAll('td')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim());
                    const obj = {};
                    headers.forEach((h,i)=>obj[h]=cells[i]||'');
                    return obj;
                }).filter(r => Object.values(r).some(Boolean));
            }''', headers)
            for r in page_rows:
                key = tuple_key = tuple(r.get(h,'') for h in headers)
                if key not in {tuple(x.get(h,'') for h in headers) for x in rows}:
                    rows.append(r)

            next_btn = page.locator('button.p-paginator-next')
            if not await next_btn.count():
                break
            disabled = await next_btn.first.evaluate("el => el.classList.contains('p-disabled') || el.disabled")
            if disabled:
                break
            await next_btn.first.click(timeout=10000)
            await page.wait_for_timeout(1800)
            if seen_pages > 50:
                raise RuntimeError('Pagination safety stop >50 pages')

        await page.screenshot(path=str(WORK / 'sb-broadcast-templates-filtered.png'), full_page=True)
        await browser.close()

    # Write CSV.
    with OUT.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=headers, lineterminator='\r\n')
        w.writeheader(); w.writerows(rows)

    # Update Google Sheet tab.
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
    token = access_token()
    def api(method, url, data=None):
        headers_api={'Authorization':'Bearer '+token}
        body_api=None
        if data is not None:
            body_api=json.dumps(data).encode(); headers_api['Content-Type']='application/json; charset=UTF-8'
        req=urllib.request.Request(url, method=method, headers=headers_api, data=body_api)
        with urllib.request.urlopen(req, timeout=60) as r:
            raw=r.read(); return json.loads(raw) if raw else {}

    ss = api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
    existing = {s['properties']['title']: s['properties']['sheetId'] for s in ss.get('sheets',[])}
    if SHEET_TAB not in existing:
        api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests':[{'addSheet': {'properties': {'title': SHEET_TAB}}}]})
        ss = api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
        existing = {s['properties']['title']: s['properties']['sheetId'] for s in ss.get('sheets',[])}
    values = [headers] + [[r.get(h,'') for h in headers] for r in rows]
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SHEET_TAB)}!A:Z:clear', {})
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate', {
        'valueInputOption':'RAW',
        'data':[{'range': f"'{SHEET_TAB}'!A1", 'majorDimension':'ROWS', 'values': values}]
    })
    sid = existing[SHEET_TAB]
    api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate', {'requests':[
        {'updateSheetProperties': {'properties': {'sheetId': sid, 'gridProperties': {'frozenRowCount': 1}}, 'fields':'gridProperties.frozenRowCount'}},
        {'repeatCell': {'range': {'sheetId': sid, 'startRowIndex':0, 'endRowIndex':1}, 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': {'red':0.86,'green':0.92,'blue':1.0}}}, 'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
        {'autoResizeDimensions': {'dimensions': {'sheetId': sid, 'dimension':'COLUMNS', 'startIndex':0, 'endIndex':len(headers)}}},
    ]})
    rb = api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SHEET_TAB)}!A:A')
    readback_count = max(0, len(rb.get('values',[]))-1)
    print(json.dumps({
        'status':'OK',
        'headers': headers,
        'rows': len(rows),
        'csv': str(OUT),
        'screenshot': str(WORK / 'sb-broadcast-templates-filtered.png'),
        'sheet_tab': SHEET_TAB,
        'sheet_url': f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
        'readback_count': readback_count,
        'sample': rows[:5],
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
