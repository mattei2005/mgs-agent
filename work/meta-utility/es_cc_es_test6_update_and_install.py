#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import asyncio, csv, datetime, json, pathlib, re, urllib.parse, urllib.request, urllib.error
from copy import deepcopy
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

SHEET_ID = '1ieSjYbhl34T0tWOvvol3F2lhvCoVTWHm9_YnUkoVhtM'
SOURCE_TAB = 'ES-CC-ES'
SUMMARY_TAB = 'ES-CC-ES Approval Summary'
TEST6_TEMPLATE = 'teste-6-es-cc-es-test5-sem-status-reapproval'
TARGET_TEMPLATES = [
    'Wantabrand - ES-CC-ES/ES-ZW - M2 - g001-d Icaro',
    'Fincgriffin - ES-CC-ES/ES-ZW-SR - g006-d Nicolas',
    'Fincgriffin - ES-CC-ES/ES-ZW-SR - g001-d Icaro',
    'Fincgriffin - ES-CC-ES/ES-ZW-SR - g003-d Isliago',
    'Fincgriffin - ES-CC-ES/ES-ZW-SR - g004-d Joe',
    'Fincgriffin - ES-CC-ES/ES-ZW-SR - g005-d Kelly',
    'ZytivaFinanzas - ES-CC-ES/ES-ZW-SR - g003-d Isliago',
    'Openzed - ES-CC-ES/ES-ZW - AV - g003-d Isliago',
]
WORK = pathlib.Path('/root/mgs-agent/work/meta-utility/es-cc-es-apply-best70-20260630')
BACKUP_DIR = pathlib.Path('/root/mgs-agent/backups/sb-templates')
TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
ZW_RE = re.compile('[\u200b\u200c\u200d\ufeff\u2060]')
NOW = datetime.datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d-%H%M%S')


def visible(s):
    return ZW_RE.sub('', s or '')


def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', s.lower()).strip('-')[:90]


def parse_messages(row):
    msgs = row.get('MESSAGES') or '[]'
    if isinstance(msgs, str):
        return json.loads(msgs)
    return msgs


def status_of(m):
    vals = {k:int(m.get(k) or 0) for k in ('APPROVED','INVALID_FORMAT','REJECTED','ERROR')}
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


def status_counts(rows):
    from collections import Counter
    return dict(Counter(r.get('STATUS','') for r in rows))


def score_row(row):
    text = visible(row.get('TEXT','')).lower()
    cta = row.get('CTA 1','').lower()
    score = 0
    strong = ['aprobado','autorizado','límite','limite','tarjeta','crédito','credito','entrega','paquete','estado','confirm','verificar','revisión','revision','desbloqueada','virtual','platinum','priority','prioridad']
    for term in strong:
        if term in text: score += 9
    for term in ['urgente','ahora','hoy','retenido','no reclamado','nuevo estado','cambió','cambio','lista','listo','final']:
        if term in text: score += 5
    for term in ['confirmar','revisar','activar','abrir','leer','finalizar','verificar','desbloquear','entrega']:
        if term in cta: score += 6
    if '{{first_name}}' in row.get('TEXT',''): score += 5
    if any(ch in row.get('TEXT','') for ch in '✅🔔📦💳🚚⚠️📍🏠📬📋🟢🔓🏆'): score += 5
    ln = len(visible(row.get('TEXT','')))
    if 90 <= ln <= 430: score += 8
    if ln < 55: score -= 10
    if 'solicitud' in text and ('tarjeta' in text or 'crédito' in text or 'credito' in text): score += 8
    # Business risk penalty; do not fully exclude if already approved, just rank below cleaner copy.
    for risky in ['banco ha liberado oficialmente sus fondos','fondos','€ 14,200','$ 14,200','€15,000','$15,000','mensajero','correo local']:
        if risky in text: score -= 8
    try:
        mid = int(row.get('MESSAGE ID') or 9999)
    except Exception:
        mid = 9999
    return score, -mid


def normalize_sheet_rows(values):
    header = list(values[0])
    rows=[]
    for line in values[1:]:
        obj={h:(line[i] if i < len(line) else '') for i,h in enumerate(header)}
        rows.append(obj)
    return header, rows


def update_sheet_from_test6(test6_messages):
    token=access_token()
    current = gapi(token, 'GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SOURCE_TAB)}!A:Z')
    backup_path = WORK / f'es-cc-es-before-test6-status-update-{NOW}.json'
    backup_path.write_text(json.dumps(current, ensure_ascii=False, indent=2))
    values=current.get('values', [])
    if not values: raise RuntimeError(f'{SOURCE_TAB} empty')
    header, rows = normalize_sheet_rows(values)
    for col in ['STATUS','APPROVED','REJECTED','INVALID_FORMAT','ERROR','REJECTED_REASON','SOURCE_TEMPLATE','TEMPLATE_ID']:
        if col not in header:
            header.append(col)
    by_id = {str(m.get('MESSAGE_ID') or m.get('MESSAGE ID')): m for m in test6_messages}
    approved_updates=0; all_updates=0
    for r in rows:
        mid=str(r.get('MESSAGE ID','')).strip()
        if mid in by_id:
            m=by_id[mid]; st=status_of(m)
            # Rodolfo asked to update messages that were approved; keep negative/raw fields too for audit.
            if st == 'APPROVED':
                r['STATUS']='APPROVED'; approved_updates += 1
            elif not r.get('STATUS'):
                r['STATUS']=st
            for k in ['APPROVED','REJECTED','INVALID_FORMAT','ERROR']:
                r[k]=str(m.get(k,0) or 0)
            r['REJECTED_REASON']=json.dumps(m.get('REJECTED_REASON',{}), ensure_ascii=False) if m.get('REJECTED_REASON') else ''
            r['SOURCE_TEMPLATE']=TEST6_TEMPLATE
            all_updates += 1
    out=[header] + [[r.get(h,'') for h in header] for r in rows]
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SOURCE_TAB)}!A:Z:clear',{})
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate',{
        'valueInputOption':'RAW',
        'data':[{'range': f"'{SOURCE_TAB}'!A1", 'majorDimension':'ROWS', 'values': out}]
    })
    ss=gapi(token,'GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(sheetId,title))')
    tabs={s['properties']['title']:s['properties']['sheetId'] for s in ss.get('sheets',[])}
    if SUMMARY_TAB not in tabs:
        gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate',{'requests':[{'addSheet':{'properties':{'title':SUMMARY_TAB}}}]})
    counts=status_counts(rows)
    summary=[['Template', TEST6_TEMPLATE], ['Updated ET', datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')], ['Rows in Sheet', len(rows)], ['Test6 messages', len(test6_messages)], ['Approved updates from Test6', approved_updates]] + [[k or 'BLANK', v] for k,v in sorted(counts.items())]
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SUMMARY_TAB)}!A:Z:clear',{})
    gapi(token,'POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate',{'valueInputOption':'RAW','data':[{'range':f"'{SUMMARY_TAB}'!A1",'majorDimension':'ROWS','values':summary}]})
    rb=gapi(token,'GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(SOURCE_TAB)}!A:A')
    return rows, {'backup':str(backup_path),'readback_rows':max(0,len(rb.get('values',[]))-1),'counts':counts,'approved_updates':approved_updates,'all_updates':all_updates}


def selected_best70(sheet_rows):
    approved=[r for r in sheet_rows if r.get('STATUS') == 'APPROVED']
    if len(approved) < 70:
        raise RuntimeError(f'Only {len(approved)} approved rows available; need 70')
    # Deduplicate visible text + CTA, rank by appeal.
    seen=set(); unique=[]
    for r in sorted(approved, key=score_row, reverse=True):
        key=(visible(r.get('TEXT','')).strip().lower(), r.get('CTA 1','').strip().lower())
        if key in seen: continue
        seen.add(key); unique.append(r)
        if len(unique) == 70: break
    if len(unique) < 70: raise RuntimeError(f'Only {len(unique)} unique approved rows after dedupe')
    bank=[]
    for i,r in enumerate(unique, 1):
        bank.append({
            'MESSAGE_ID': i,
            'TEXT': r.get('TEXT',''),
            'DESCRIPTION': r.get('DESCRIPTION',''),
            'IMAGE': r.get('IMAGE',''),
            'CTA_1': r.get('CTA 1',''),
            'LINK_1': r.get('LINK 1',''),
            'CTA_2': r.get('CTA 2',''),
            'LINK_2': r.get('LINK 2',''),
            'TEXT_2': r.get('TEXT 2',''),
            'SOURCE_MESSAGE_ID': r.get('MESSAGE ID',''),
            'SCORE': score_row(r)[0],
        })
    (WORK/'es-cc-es-approved-best70-selected-bank.json').write_text(json.dumps(bank, ensure_ascii=False, indent=2))
    with (WORK/'es-cc-es-approved-best70-selected-bank.csv').open('w', encoding='utf-8-sig', newline='') as f:
        cols=['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2','SOURCE_MESSAGE_ID','SCORE']
        w=csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n'); w.writeheader()
        for m in bank:
            w.writerow({'MESSAGE ID':m['MESSAGE_ID'],'TEXT':m['TEXT'],'DESCRIPTION':m['DESCRIPTION'],'IMAGE':m['IMAGE'],'CTA 1':m['CTA_1'],'LINK 1':m['LINK_1'],'CTA 2':m['CTA_2'],'LINK 2':m['LINK_2'],'TEXT 2':m['TEXT_2'],'SOURCE_MESSAGE_ID':m['SOURCE_MESSAGE_ID'],'SCORE':m['SCORE']})
    return bank, len(approved)


async def capture_rows_and_headers():
    captured_rows=[]; captured_headers=None; post_url='https://api.jbfdigital.com.br/broadcast/Messenger'
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(storage_state='/tmp/smartbidding_state_headed.json', viewport={'width':1600,'height':1000}, user_agent=UA)
    page = await ctx.new_page()
    async def on_request(req):
        nonlocal captured_headers, post_url
        if '/broadcast/Messenger' in req.url and req.method == 'GET':
            captured_headers = req.headers
            post_url = req.url.split('?')[0]
    async def on_response(resp):
        if '/broadcast/Messenger' in resp.url and resp.status == 200:
            try:
                data=await resp.json()
                if isinstance(data, list): captured_rows.extend(data)
            except Exception:
                pass
    page.on('request', on_request); page.on('response', on_response)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='networkidle', timeout=90000)
    await page.wait_for_timeout(2500)
    try:
        await page.locator('.p-dropdown').first.click(timeout=10000)
        await page.wait_for_timeout(500)
        await page.get_by_text('Messenger', exact=True).last.click(timeout=10000)
        await page.wait_for_timeout(2500)
    except Exception:
        pass
    await page.get_by_text('Broadcast Template', exact=True).click(timeout=15000)
    await page.wait_for_timeout(7000)
    if not captured_headers or not captured_rows:
        await browser.close(); await p.stop()
        raise RuntimeError('Could not capture /broadcast/Messenger rows and headers')
    # Dedupe latest by ID/NAME
    dedup={}
    for r in captured_rows:
        dedup[r.get('ID') or r.get('NAME')]=r
    rows=list(dedup.values())
    # sanitize request headers. Keep auth/runtime headers, drop browser-only pseudo headers.
    headers={k:v for k,v in captured_headers.items() if not k.startswith(':') and k.lower() not in ('content-length','host')}
    headers['content-type']='application/json'
    return p, browser, ctx, page, rows, headers, post_url


def build_target_messages(bank, target_msgs):
    ordered=sorted(target_msgs, key=lambda m:int(m.get('MESSAGE_ID') or 0))
    if not ordered: raise RuntimeError('target template has no messages')
    link_seq=[m.get('LINK_1','') for m in ordered]
    cta2_seq=[m.get('CTA_2','') for m in ordered]
    link2_seq=[m.get('LINK_2','') for m in ordered]
    out=[]
    for i,b in enumerate(bank, 1):
        m={
            'MESSAGE_ID': i,
            'TEXT': b['TEXT'],
            'DESCRIPTION': b.get('DESCRIPTION',''),
            'IMAGE': b.get('IMAGE',''),
            'CTA_1': b.get('CTA_1',''),
            'LINK_1': link_seq[(i-1) % len(link_seq)],
            'CTA_2': cta2_seq[(i-1) % len(cta2_seq)] if cta2_seq else '',
            'LINK_2': link2_seq[(i-1) % len(link2_seq)] if link2_seq else '',
            'TEXT_2': '',
        }
        out.append(m)
    return out


async def update_templates(bank, initial_rows=None):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    p, browser, ctx, page, rows, headers, post_url = await capture_rows_and_headers()
    row_by_name={r.get('NAME'):r for r in rows}
    missing=[n for n in [TEST6_TEMPLATE]+TARGET_TEMPLATES if n not in row_by_name]
    if missing: raise RuntimeError('Missing template(s): '+json.dumps(missing, ensure_ascii=False))
    test6_msgs=sorted(parse_messages(row_by_name[TEST6_TEMPLATE]), key=lambda m:int(m.get('MESSAGE_ID') or 0))
    # If sheet not updated yet, caller can use this.
    results=[]
    try:
        for name in TARGET_TEMPLATES:
            row=row_by_name[name]
            before_msgs=parse_messages(row)
            backup_json=BACKUP_DIR/f'{safe_name(name)}-before-es-cc-es-best70-{NOW}.json'
            backup_csv=BACKUP_DIR/f'{safe_name(name)}-before-es-cc-es-best70-{NOW}.csv'
            backup_json.write_text(json.dumps(row, ensure_ascii=False, indent=2))
            with backup_csv.open('w', encoding='utf-8-sig', newline='') as f:
                cols=['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2','APPROVED','REJECTED','INVALID_FORMAT','ERROR']
                w=csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n'); w.writeheader()
                for m in sorted(before_msgs, key=lambda x:int(x.get('MESSAGE_ID') or 0)):
                    w.writerow({'MESSAGE ID':m.get('MESSAGE_ID',''),'TEXT':m.get('TEXT',''),'DESCRIPTION':m.get('DESCRIPTION',''),'IMAGE':m.get('IMAGE',''),'CTA 1':m.get('CTA_1',''),'LINK 1':m.get('LINK_1',''),'CTA 2':m.get('CTA_2',''),'LINK 2':m.get('LINK_2',''),'TEXT 2':m.get('TEXT_2',''),'APPROVED':m.get('APPROVED',''),'REJECTED':m.get('REJECTED',''),'INVALID_FORMAT':m.get('INVALID_FORMAT',''),'ERROR':m.get('ERROR','')})
            payload=deepcopy(row)
            new_msgs=build_target_messages(bank, before_msgs)
            payload['MESSAGES']=json.dumps(new_msgs, ensure_ascii=False, separators=(',',':'))
            resp=await ctx.request.post(post_url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
            if resp.status >= 300:
                txt=await resp.text()
                raise RuntimeError(f'POST failed {name}: HTTP {resp.status} {txt[:300]}')
            results.append({'name':name,'id':row.get('ID'),'before_count':len(before_msgs),'after_target':len(new_msgs),'backup_json':str(backup_json),'backup_csv':str(backup_csv),'post_status':resp.status,'first_link':new_msgs[0]['LINK_1'],'last_link':new_msgs[-1]['LINK_1']})
        # Re-open/refresh capture by going to tab again and validate via fresh GET response.
        rows2=[]
        async def on_response2(resp):
            if '/broadcast/Messenger' in resp.url and resp.status == 200:
                try:
                    data=await resp.json()
                    if isinstance(data, list): rows2.extend(data)
                except Exception:
                    pass
        page.on('response', on_response2)
        await page.reload(wait_until='networkidle', timeout=90000)
        await page.wait_for_timeout(5000)
        dedup={}
        for r in rows2:
            dedup[r.get('ID') or r.get('NAME')]=r
        validation=[]
        by_name2={r.get('NAME'):r for r in dedup.values()}
        for name in TARGET_TEMPLATES:
            r=by_name2.get(name)
            if not r:
                validation.append({'name':name,'validated':False,'error':'not found after reload'})
                continue
            msgs=parse_messages(r)
            validation.append({'name':name,'validated':len(msgs)==70,'count':len(msgs),'first_text_visible':visible(msgs[0].get('TEXT',''))[:80] if msgs else '', 'last_text_visible':visible(msgs[-1].get('TEXT',''))[:80] if msgs else ''})
        return test6_msgs, results, validation
    finally:
        try:
            await browser.close()
        except Exception:
            pass
        try:
            await p.stop()
        except Exception:
            pass


async def main():
    WORK.mkdir(parents=True, exist_ok=True)
    # First capture once to get Test6 messages, update Sheet, select bank, then capture/update templates.
    p, browser, ctx, page, rows, headers, post_url = await capture_rows_and_headers()
    try:
        row_by_name={r.get('NAME'):r for r in rows}
        if TEST6_TEMPLATE not in row_by_name:
            raise RuntimeError(f'Test6 template not found: {TEST6_TEMPLATE}')
        test6_msgs=sorted(parse_messages(row_by_name[TEST6_TEMPLATE]), key=lambda m:int(m.get('MESSAGE_ID') or 0))
    finally:
        try:
            await browser.close()
        except Exception:
            pass
        try:
            await p.stop()
        except Exception:
            pass
    (WORK/'test6-es-cc-es-reapproval-raw.json').write_text(json.dumps(test6_msgs, ensure_ascii=False, indent=2))
    with (WORK/'test6-es-cc-es-reapproval-status.csv').open('w', encoding='utf-8-sig', newline='') as f:
        cols=['MESSAGE ID','TEXT','CTA 1','STATUS','APPROVED','REJECTED','INVALID_FORMAT','ERROR']
        w=csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n'); w.writeheader()
        for m in test6_msgs:
            w.writerow({'MESSAGE ID':m.get('MESSAGE_ID',''),'TEXT':visible(m.get('TEXT','')),'CTA 1':m.get('CTA_1',''),'STATUS':status_of(m),'APPROVED':m.get('APPROVED',0),'REJECTED':m.get('REJECTED',0),'INVALID_FORMAT':m.get('INVALID_FORMAT',0),'ERROR':m.get('ERROR',0)})
    sheet_rows, sheet_info = update_sheet_from_test6(test6_msgs)
    bank, approved_available = selected_best70(sheet_rows)
    # Guard: Spanish ES bank should not contain EN phrases in bulk; allow URLs to be replaced by target links.
    sample_visible='\n'.join(visible(m['TEXT']) for m in bank[:10]).lower()
    if 'credit card approved' in sample_visible or 'your card' in sample_visible:
        raise RuntimeError('Language guard failed: English marker in selected bank')
    test6_msgs2, update_results, validation = await update_templates(bank)
    audit={
        'status':'OK',
        'executed_at_et':datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),
        'source_tab':SOURCE_TAB,
        'test6_template':TEST6_TEMPLATE,
        'test6_messages':len(test6_msgs),
        'test6_counts':{s:sum(1 for m in test6_msgs if status_of(m)==s) for s in ['', 'APPROVED','REJECTED','INVALID_FORMAT','ERROR']},
        'sheet_info':sheet_info,
        'approved_available_after_update':approved_available,
        'selected_bank_count':len(bank),
        'selected_bank_json':str(WORK/'es-cc-es-approved-best70-selected-bank.json'),
        'selected_bank_csv':str(WORK/'es-cc-es-approved-best70-selected-bank.csv'),
        'targets_requested':TARGET_TEMPLATES,
        'update_results':update_results,
        'validation':validation,
        'all_validated':all(v.get('validated') for v in validation) and len(validation)==len(TARGET_TEMPLATES),
        'sheet_url':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit',
    }
    (WORK/'es-cc-es-test6-update-and-apply-best70-results.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps({
        'status':audit['status'],
        'test6_counts':audit['test6_counts'],
        'sheet_counts':audit['sheet_info']['counts'],
        'approved_available_after_update':approved_available,
        'selected_bank_count':len(bank),
        'templates_updated':len(update_results),
        'all_validated':audit['all_validated'],
        'validation_counts':[{'name':v['name'], 'count':v.get('count'), 'validated':v.get('validated')} for v in validation],
        'audit':str(WORK/'es-cc-es-test6-update-and-apply-best70-results.json')
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
