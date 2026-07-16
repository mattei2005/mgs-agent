#!/usr/bin/env python3
"""DTR -> SmartBidding page health sync.

Validated workflow:
- active bot users from migration Sheet only;
- DigitalTRChat account/segurador -> real page selector -> search_page_id per page;
- latest Completed report only;
- update SB NOTES for every non-Sent result, all SB statuses;
- apply/clear RESTRICTED_UNTIL only with validated rules;
- Blocked rows require dual diagnosis before reactivation: the page can be
  blocked/down, or the segurador/Facebook profile can be down while the page
  is still public. Never restore Blocked -> Broadcast from public FB URL alone.
"""
import argparse, asyncio, csv, fcntl, html, importlib.util, io, json, os, re, subprocess, sys, tempfile, unicodedata, urllib.error, urllib.parse, urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE_DIR=Path('/root/mgs-agent')
SHEET_ID='1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY'
MIGRATION_GID='562940072'
MIGRATION_GID_FALLBACKS=['562940072','85508562','136896597']
DTR_BASE='https://digitaltrchat.com'
SB_STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
NY=ZoneInfo('America/New_York')
LOG_DIR=BASE_DIR/'logs'
REPORT_DIR=BASE_DIR/'reports'
STATE_PATH=BASE_DIR/'data/dtr-sb-page-health-sync-state.json'
TARGET_CHANNEL_ID='1522442220903337984'
OP_RESOLVER_PATH=BASE_DIR/'scripts/mgs-op-item-resolver.py'
REPORT_SHEET_ID='1sIBGA_CHMtHF1mWgsvjUHfEkvuF3pb9VC5oeg06tHsI'
REPORT_SHEET_URL=f'https://docs.google.com/spreadsheets/d/{REPORT_SHEET_ID}/edit?gid=0#gid=0'
REPORT_TOTAL_TAB='Paginas Totais'
REPORT_SUMMARY_TAB='Resumo'
REPORT_LEGACY_TOTAL_TAB='Paginas'
REPORT_SHEET_LOCK=Path('/var/lock/sb-restricted-sheet-writer.lock')
GOOGLE_TOKEN_FILE=BASE_DIR/'.secrets/ares-google-drive-oauth-client.json'
GLOBAL_IGNORE_PATH=BASE_DIR/'data/mgs-global-page-ignore-list.json'

_op_spec=importlib.util.spec_from_file_location('mgs_op_item_resolver', OP_RESOLVER_PATH)
if not _op_spec or not _op_spec.loader:
    raise RuntimeError(f'cannot load 1Password resolver: {OP_RESOLVER_PATH}')
OP_RESOLVER=importlib.util.module_from_spec(_op_spec)
_op_spec.loader.exec_module(OP_RESOLVER)

MONTHS_EN={'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}
MONTHS_PT={'janeiro':1,'fevereiro':2,'março':3,'marco':3,'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12}
MONTHS_ES={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12}


def norm(v): return '' if v is None else str(v).strip()
def norm_email(v): return norm(v).lower()
def clean(v): return html.unescape(re.sub(r'<[^>]+>',' ',str(v or ''))).replace('\u202f',' ').replace('\xa0',' ').strip()
def norm_name(v):
    t=clean(v).lower()
    t=''.join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c))
    t=re.sub(r'[^a-z0-9]+',' ',t)
    return re.sub(r'\s+',' ',t).strip()
def today(): return datetime.now(NY).date().isoformat()
def now_iso(): return datetime.now(NY).isoformat(timespec='seconds')
def date_only(v): return norm(v)[:10]

STEP1_NOISE_NAMES={norm_name(x) for x in ['Rodolfo Mattei','Geizian Pereira']}
STEP1_ACTIVE_OVERRIDES=[
    {'user':'disparoseggbev@gmail.com','segurador':'Andi Setiawan','app':'B003'},
    {'user':'disparosfincgriffinuscaren003@gmail.com','segurador':'Karoline Chaves','app':'B002'},
    {'user':'disparosinfinitynexx@gmail.com','segurador':'Akew Rider','app':'B009'},
    {'user':'disparosinfinitynexx@gmail.com','segurador':'Anggiat Hutajulu','app':'B009'},
]

def sheet_rows():
    # Google's `/export?format=csv&gid=...` route intermittently returns 400
    # and the migration workbook has changed tabs over time. Try the known gids
    # and use the first tab that returns rows with User + Segurador.
    last=[]
    for gid in MIGRATION_GID_FALLBACKS:
        url=f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={gid}'
        data=urllib.request.urlopen(url, timeout=60).read().decode('utf-8-sig')
        rows=list(csv.DictReader(io.StringIO(data))) if data.strip() else []
        last=rows
        if rows and 'User' in rows[0] and 'Segurador' in rows[0]:
            return rows
    return last

def active_users_from_sheet(rows):
    users=[]
    for r in rows:
        u=norm_email(r.get('User'))
        if '@' not in u: continue
        if 'NO APP' in r and not norm(r.get('NO APP')): continue
        if 'Migrado' in r and norm(r.get('Migrado')).upper() not in {'TRUE','OK','SIM','YES','1'}: continue
        if norm(r.get('Removidos acumulado')).upper()=='X': continue
        users.append(u)
    return sorted(set(users))

def build_step1_scope(rows):
    scope={'active':defaultdict(dict),'x':defaultdict(dict),'overrides':defaultdict(dict),'row_counts':Counter()}
    for r in rows:
        u=norm_email(r.get('User'))
        name=clean(r.get('Segurador'))
        key=norm_name(name)
        if '@' not in u or not key:
            continue
        if 'NO APP' in r and not norm(r.get('NO APP')):
            continue
        if 'Migrado' in r and norm(r.get('Migrado')).upper() not in {'TRUE','OK','SIM','YES','1'}:
            continue
        rec={'user':u,'segurador':name,'norm':key,'app':norm(r.get('NO APP') or r.get('Migrado') or 'sheet'),'pg':norm(r.get('PG') or r.get('#paginas')),'removed':norm(r.get('Removidos acumulado')).upper()}
        if rec['removed']=='X':
            scope['x'][u][key]=rec; scope['row_counts']['x_rows']+=1
        else:
            scope['active'][u][key]=rec; scope['row_counts']['active_rows']+=1
    for o in STEP1_ACTIVE_OVERRIDES:
        u=norm_email(o['user']); key=norm_name(o['segurador'])
        scope['overrides'][u][key]={**o,'user':u,'norm':key,'override':True}
        scope['active'][u].setdefault(key,{**o,'user':u,'norm':key,'override':True})
    return scope

def step1_account_classification(username, account_name, occurrences, scope):
    u=norm_email(username); key=norm_name(account_name)
    if key in STEP1_NOISE_NAMES:
        return 'IGNORED_NOISE_SKIP_PAGES', 'Rodolfo/Geizian noise account'
    if key in scope['x'].get(u, {}):
        return 'IGNORED_X_SKIP_PAGES', 'sheet Removidos acumulado=X'
    if occurrences > 1:
        return 'REPORT_DUPLICATE_SKIP_PAGES', f'duplicate account occurrences={occurrences}'
    if key in scope['active'].get(u, {}) or key in scope['overrides'].get(u, {}):
        return 'PENDING_PAGE_LIST', 'active sheet/override match'
    return 'OUT_OF_SCOPE_SKIP_PAGES', 'not active in migration sheet for this bot user'

def discover_dtr_items(target_users):
    vault=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
    mapped, missing, errors, _cache=OP_RESOLVER.resolve_dtr_items(target_users, vault)
    matched={u: row['id'] for u,row in mapped.items()}
    return matched, missing, errors

def op_password(item):
    vault=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
    data=OP_RESOLVER.get_item_json(item, vault)
    return OP_RESOLVER.field_value(data, 'credential', 'password', required=True)

def parse_restricted_date(text, year=None):
    t=clean(text); y=year or datetime.now(NY).year
    m=re.search(r'until\s+([A-Za-z]+)\s+(\d{1,2})\s+at\s+(\d{1,2}):(\d{2})\s*([AP]M)', t, re.I)
    if m:
        mon=MONTHS_EN.get(m.group(1).lower()); day=int(m.group(2)); hh=int(m.group(3)); mm=int(m.group(4)); ap=m.group(5).upper()
        if mon:
            if ap=='PM' and hh!=12: hh+=12
            if ap=='AM' and hh==12: hh=0
            return f'{y:04d}-{mon:02d}-{day:02d}', f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}'
    m=re.search(r'at[eé]\s+(\d{1,2})\s+de\s+([A-Za-záéíóúãõç]+)\s+às\s+(\d{1,2}):(\d{2})', t, re.I)
    if m:
        day=int(m.group(1)); mon=MONTHS_PT.get(m.group(2).lower()); hh=int(m.group(3)); mm=int(m.group(4))
        if mon:
            return f'{y:04d}-{mon:02d}-{day:02d}', f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}'
    m=re.search(r'hasta\s+el\s+(\d{1,2})\s+de\s+([A-Za-záéíóúñ]+)\s+a\s+las\s+(\d{1,2}):(\d{2})\s*([ap])\.\s*m\.', t, re.I)
    if m:
        day=int(m.group(1)); mon=MONTHS_ES.get(m.group(2).lower()); hh=int(m.group(3)); mm=int(m.group(4)); ap=m.group(5).lower()
        if mon:
            if ap=='p' and hh!=12: hh+=12
            if ap=='a' and hh==12: hh=0
            return f'{y:04d}-{mon:02d}-{day:02d}', f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}'
    return None, None

def date_from_text(text):
    t=clean(text)
    m=re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s*\d{2}\s+\d{1,2}:\d{2}\b', t, re.I)
    return m.group(0) if m else ''

def classify_report(raw):
    t=clean(raw); low=t.lower(); codes=[]
    checks=[('#2022',['#2022','temporarily restricted','restring']),('#10',['#10','outside of allowed window','fora do espaço de tempo permitido','fuera del período permitido']),('#551',['#551',"isn't available",'não está disponível','no se encuentra disponible']),('#100',['#100','missing one or more params','no matching user found','não foi possível encontrar o modelo','no se puede encontrar la plantilla']),('APP_DELETED',['application has been deleted','aplicativo foi excluído']),('PERMISSION',['pages_messaging permission','permission(s) must be granted','before impersonatin']),('TOKEN',['oauth','token','session'])]
    for code, needles in checks:
        if any(n.lower() in low for n in needles): codes.append(code)
    ru,rut=parse_restricted_date(t)
    if not codes:
        if re.search(r'\bSent\b|Enviado|Delivered|Entregado', t, re.I):
            return {'status':'SENT','codes':[], 'note_code':'', 'restricted_until':None, 'restricted_until_time':None, 'raw':t[:1200]}
        return {'status':'NO_CAMPAIGN_DATA_YET' if not t else 'OTHER', 'codes':([] if not t else ['OTHER']), 'note_code':('' if not t else 'OTHER'), 'restricted_until':None, 'restricted_until_time':None, 'raw':t[:1200]}
    return {'status':'ERROR','codes':codes,'note_code':' - '.join(codes),'restricted_until':ru,'restricted_until_time':rut,'raw':t[:1200]}

def campaign_form(csrf, page_id, length=10):
    form={'draw':'1','start':'0','length':str(length),'search_page_id':str(page_id),'search_value':'','search_status':'2','campaign_date_range':'','csrf_token':csrf,'order[0][column]':'12','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
    for i in range(14):
        form[f'columns[{i}][data]']=str(i); form[f'columns[{i}][searchable]']='true'; form[f'columns[{i}][orderable]']='true'; form[f'columns[{i}][search][value]']=''; form[f'columns[{i}][search][regex]']='false'
    return form

def report_form(csrf, campaign_id, length=100):
    form={'draw':'1','start':'0','length':str(length),'campaign_id':str(campaign_id),'csrf_token':csrf,'order[0][column]':'3','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
    for i in range(9):
        form[f'columns[{i}][data]']=str(i); form[f'columns[{i}][searchable]']='true'; form[f'columns[{i}][orderable]']='true'; form[f'columns[{i}][search][value]']=''; form[f'columns[{i}][search][regex]']='false'
    return form

async def dtr_post_json(ctx, url, form, ref):
    r=await ctx.request.post(url, form=form, headers={'X-Requested-With':'XMLHttpRequest','Referer':ref}, timeout=60000)
    txt=await r.text()
    try: return json.loads(txt) if txt else {}
    except Exception: return {'_parse_error':txt[:500], '_status':r.status}

def campaign_id_from_row(row):
    for cell in row:
        m=re.search(r"cam-id=['\"]?(\d+)", str(cell))
        if m: return m.group(1)
    return ''

def fb_id_from_row(row):
    txt=' '.join(str(x) for x in row)
    for pat in [r'facebook\.com\\?/(\d+)', r'facebook\.com/(\d+)', r'facebook\.com%2F(\d+)']:
        m=re.search(pat, txt)
        if m: return m.group(1)
    return ''

async def scan_dtr_user(username, item, step1_scope, limit_accounts=0, limit_pages=0, skip_restricted_pages=None):
    skip_restricted_pages=set(skip_restricted_pages or [])
    out={'username':username,'accounts':[], 'reports':[], 'errors':[], 'login_ok':False}
    try:
        password=op_password(item)
    except Exception as exc:
        out['errors'].append(f'credential_error: {type(exc).__name__}: {exc}')
        return out
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(viewport={'width':1600,'height':1000})
        page=await ctx.new_page(); url=f'{DTR_BASE}/messenger_bot_enhancers/subscriber_broadcast_campaign'
        try:
            await page.goto(f'{DTR_BASE}/home/login', wait_until='domcontentloaded', timeout=60000)
            inputs=page.locator('input:visible'); await inputs.nth(0).fill(username); await inputs.nth(1).fill(password)
            await page.locator('button:visible, input[type=submit]:visible').last.click(); await page.wait_for_timeout(3500)
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            csrf=await page.locator('#csrf_token').input_value(timeout=10000); out['login_ok']=True
            accs=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el=>({id:el.getAttribute('data-id')||el.dataset.id||'', name:(el.innerText||el.textContent||'').trim()})).filter(x=>x.id||x.name)""")
            if not accs: accs=[{'id':'','name':'default'}]
            seen=set(); uniq=[]
            for a in accs:
                k=(a.get('id','')+'|'+a.get('name','')).strip()
                if k not in seen: seen.add(k); uniq.append(a)
            if limit_accounts: uniq=uniq[:limit_accounts]
            name_counts=Counter(norm_name(a.get('name') or 'default') for a in uniq)
            signatures=[]
            for a in uniq:
                aid=a.get('id') or ''; aname=clean(a.get('name') or 'default') or 'default'
                step1_status, step1_reason = step1_account_classification(username, aname, name_counts[norm_name(aname)], step1_scope)
                acc={'id':aid,'name':aname,'pages':0,'latest_completed':0,'no_completed':0,'skipped_already_restricted':0,'signature':[],'errors':[],'step1_status':step1_status,'step1_reason':step1_reason}
                out['accounts'].append(acc)
                if step1_status != 'PENDING_PAGE_LIST':
                    continue
                try:
                    if aid:
                        await ctx.request.post(f'{DTR_BASE}/social_accounts/fb_rx_account_switch', form={'id':aid,'csrf_token':csrf}, headers={'X-Requested-With':'XMLHttpRequest','Referer':url}, timeout=60000)
                        await page.goto(url, wait_until='domcontentloaded', timeout=60000); await page.wait_for_timeout(700)
                        csrf=await page.locator('#csrf_token').input_value(timeout=10000)
                    opts=await page.evaluate("""() => Array.from(document.querySelectorAll('select#search_page_id option, select[name=search_page_id] option')).map(o=>({value:o.value||'', text:(o.innerText||o.textContent||'').trim()})).filter(x=>x.value && x.value!='0' && !/select|page/i.test(x.text))""")
                    if limit_pages: opts=opts[:limit_pages]
                    acc['pages']=len(opts)
                    if not opts:
                        acc['step1_status']='NO_PAGES_REPORT_IGNORE'
                        acc['step1_reason']='single active account with zero DTR pages'
                        continue
                    acc['step1_status']='VALID_FOR_STEP2'
                    acc['step1_reason']='active account with pages present'
                    sig=[]
                    for opt in opts:
                        page_id=str(opt['value']); page_name=clean(opt['text'])
                        if page_id in skip_restricted_pages:
                            acc['skipped_already_restricted']+=1
                            continue
                        camp=await dtr_post_json(ctx, url+'_data', campaign_form(csrf,page_id), url)
                        rows=camp.get('data') or []
                        cid=''; crow=None
                        for r in rows:
                            cid=campaign_id_from_row(r)
                            if cid: crow=r; break
                        if not cid:
                            acc['no_completed']+=1
                            cls={'status':'NO_CAMPAIGN_DATA_YET','codes':[],'note_code':'','restricted_until':None,'restricted_until_time':None,'raw':''}
                            out['reports'].append({'bot_user':username,'account_id':aid,'account_name':aname,'dtr_page_id':page_id,'page_name':page_name,'fb_page_id':'','campaign_id':'','completed_date':'','classification':cls})
                            continue
                        acc['latest_completed']+=1; sig.append(cid)
                        rep=await dtr_post_json(ctx, f'{DTR_BASE}/messenger_bot_enhancers/campaign_sent_status_data', report_form(csrf,cid), url)
                        raw=' '.join(' '.join(str(x) for x in rr) for rr in (rep.get('data') or []))
                        cls=classify_report(raw)
                        out['reports'].append({'bot_user':username,'account_id':aid,'account_name':aname,'dtr_page_id':page_id,'page_name':page_name,'fb_page_id':fb_id_from_row(crow or []),'campaign_id':cid,'completed_date':date_from_text(raw) or date_from_text(' '.join(str(x) for x in (crow or []))),'classification':cls})
                    acc['signature']=sig[:10]; signatures.append(tuple(sig[:5]))
                except Exception as exc:
                    acc['errors'].append(f'{type(exc).__name__}: {exc}')
            out['context_signatures_unique']=len(set(signatures))
        except Exception as exc:
            out['errors'].append(f'{type(exc).__name__}: {exc}')
        finally:
            await browser.close()
    return out

async def get_sb_context():
    p=await async_playwright().start()
    browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=SB_STATE, viewport={'width':1600,'height':1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
    page=await ctx.new_page(); headers={}
    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            headers.update(await req.all_headers())
    page.on('request', on_req)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000); await page.wait_for_timeout(5000)
    h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}
    h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
    return p,browser,ctx,h

async def fetch_sb_rows(ctx,h):
    rc=await ctx.request.get('https://api.jbfdigital.com.br/company', headers=h, timeout=120000)
    companies=await rc.json()
    if rc.status != 200 or not isinstance(companies, list):
        raise RuntimeError(f'bad SB company response status={rc.status} type={type(companies).__name__}')
    pubs=[]
    for c in companies:
        if not isinstance(c, dict):
            raise RuntimeError('bad SB company row type')
        for pub in c.get('publishers') or []:
            if pub.get('active') and pub.get('publisherId'): pubs.append(pub['publisherId'])
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    r=await ctx.request.get('https://api.jbfdigital.com.br/campaigns/Messenger?'+qs, headers=h, timeout=120000)
    rows=await r.json()
    if r.status!=200 or not isinstance(rows,list): raise RuntimeError(f'bad SB campaigns response status={r.status}')
    return pubs, rows

def build_sb_indexes(rows):
    by_fb=defaultdict(list); by_user_page=defaultdict(list); by_user_name=defaultdict(list)
    for r in rows:
        if norm(r.get('FB_PAGE_ID')): by_fb[norm(r.get('FB_PAGE_ID'))].append(r)
        if norm(r.get('USER_LOGIN')) and norm(r.get('PAGE_ID')): by_user_page[(norm_email(r.get('USER_LOGIN')), norm(r.get('PAGE_ID')))].append(r)
        if norm(r.get('USER_LOGIN')) and norm(r.get('PAGE_NAME')): by_user_name[(norm_email(r.get('USER_LOGIN')), norm(r.get('PAGE_NAME')).lower())].append(r)
    return by_fb, by_user_page, by_user_name

def match_sb(rep, indexes):
    by_fb, by_user_page, by_user_name = indexes
    cands=[]
    fb=norm(rep.get('fb_page_id'))
    if fb: cands=by_fb.get(fb, [])
    if not cands: cands=by_user_page.get((norm_email(rep.get('bot_user')), norm(rep.get('dtr_page_id'))), [])
    if not cands: cands=by_user_name.get((norm_email(rep.get('bot_user')), norm(rep.get('page_name')).lower()), [])
    if len(cands)==1: return cands[0], None
    if not cands: return None, 'no_match'
    return None, f'ambiguous_{len(cands)}'

def append_note(existing, note_code):
    existing=norm(existing)
    code=norm(note_code)
    if not code: return existing, False
    parts=[p.strip() for p in re.split(r'\s+-\s+', code) if p.strip()]
    missing=[p for p in parts if not re.search(r'(?<![\w#])'+re.escape(p)+r'(?![\w#])', existing)]
    if not missing: return existing, False
    suffix=' - '.join(missing)
    return (existing + ' - ' + suffix) if existing else suffix, True

DELIVERY_ERROR_NOTE_CODES=['#2022','#10','#100','#551','TOKEN','APP_DELETED','PERMISSION','SEM_COMPLETED']

def strip_note_codes(existing, codes):
    """Remove transient delivery/restriction codes from SB NOTES.

    Used when DTR proves a page left restriction. Preserve the human prefix
    (segurador/site/language) and only remove exact code tokens joined by " - ".
    """
    text=norm(existing)
    if not text: return text, False
    parts=[p.strip() for p in re.split(r'\s+-\s+', text) if p.strip()]
    remove={c.upper() for c in codes}
    kept=[p for p in parts if p.upper() not in remove]
    cleaned=' - '.join(kept)
    return cleaned, cleaned != text

def active_restricted(row, tday):
    ru=date_only(row.get('RESTRICTED_UNTIL'))
    return bool(ru and ru>=tday)

def load_global_ignore_keys():
    if not GLOBAL_IGNORE_PATH.exists():
        return set(), set()
    data=json.loads(GLOBAL_IGNORE_PATH.read_text(encoding='utf-8'))
    fb_keys=set(); bot_page_keys=set()
    for entry in data.get('entries') or []:
        fb=norm(entry.get('fb_page_id'))
        bot=norm_email(entry.get('bot_user'))
        page_id=norm(entry.get('page_id_pg') or entry.get('page_id'))
        if fb: fb_keys.add(fb)
        if bot and page_id: bot_page_keys.add((bot,page_id))
    return fb_keys, bot_page_keys

def globally_ignored_page(row, fb_keys, bot_page_keys):
    fb=norm(row.get('FB_PAGE_ID'))
    bot=norm_email(row.get('USER_LOGIN') or row.get('LOGIN'))
    page_id=norm(row.get('PAGE_ID'))
    return bool((fb and fb in fb_keys) or (bot and page_id and (bot,page_id) in bot_page_keys))

def restricted_sheet_rows(sb_rows, active_users, tday):
    """Return every active restriction that must be tracked in the report Sheet.

    Broadcast remains the operational headline metric, but any other active
    restriction that can generate a transition alert (for example Campaign)
    must also exist in Paginas Totais and the corresponding site tab. On-hold
    and Blocked stay visible only as excluded counters and never become rows.
    """
    active_users={norm_email(user) for user in active_users if norm_email(user)}
    fb_ignore, bot_page_ignore=load_global_ignore_keys()
    scoped=[]; globally_ignored=0
    for row in sb_rows:
        if norm_email(row.get('USER_LOGIN') or row.get('LOGIN')) not in active_users:
            continue
        if globally_ignored_page(row,fb_ignore,bot_page_ignore):
            globally_ignored+=1
            continue
        scoped.append(row)
    restricted=[row for row in scoped if active_restricted(row,tday)]
    broadcast=[row for row in restricted if norm(row.get('STATUS')).lower()=='broadcast']
    on_hold=[row for row in restricted if norm(row.get('STATUS')).lower()=='on-hold']
    blocked=[row for row in restricted if norm(row.get('STATUS')).lower()=='blocked']
    included=[row for row in restricted if norm(row.get('STATUS')).lower() not in {'on-hold','blocked'}]
    output=[]
    for row in included:
        fb=norm(row.get('FB_PAGE_ID'))
        notes=norm(row.get('NOTES'))
        codes=[code for code in DELIVERY_ERROR_NOTE_CODES if re.search(r'(?<![\w#])'+re.escape(code)+r'(?![\w#])',notes,re.I)]
        output.append({
            'link da pagina':f'https://facebook.com/{fb}' if fb else '',
            'nome da pagina':norm(row.get('PAGE_NAME')),
            'fb page id':fb,
            'page id':norm(row.get('PAGE_ID')),
            'bot user':norm_email(row.get('USER_LOGIN') or row.get('LOGIN')),
            'segurador':norm(row.get('PROFILE_NAME')),
            'sites':derive_sites(row),
            'status sb':norm(row.get('STATUS')),
            'codigos':', '.join(codes),
            'data saida':date_only(row.get('RESTRICTED_UNTIL')),
        })
    output.sort(key=lambda row:(row.get('data saida') or '9999-99-99',row.get('nome da pagina') or '',row.get('bot user') or ''))
    return output, {
        'sheet_scope':'all active restricted pages except On-hold/Blocked; Broadcast reported separately',
        'sheet_rows_scoped':len(scoped),
        'sheet_global_ignored':globally_ignored,
        'sheet_restricted_total':len(restricted),
        'sheet_rows_included':len(included),
        'sheet_broadcast_restricted':len(broadcast),
        'sheet_on_hold_excluded':len(on_hold),
        'sheet_blocked_excluded':len(blocked),
        'sheet_other_status_included':len(included)-len(broadcast),
    }

def public_row(r):
    return {k:r.get(k) for k in ['ID','PAGE_ID','FB_PAGE_ID','PAGE_NAME','USER_LOGIN','PROFILE_NAME','STATUS','RESTRICTED_UNTIL','NOTES','BROADCAST_TEMPLATE_NAME']}

def restriction_identity(sb=None, rep=None):
    """Stable page identity for alert de-duplication.

    Do not include RESTRICTED_UNTIL/campaign/date here. Rodolfo's channel
    semantics are: a page already mentioned as restricted should not be mentioned
    again while it remains in the same unresolved restricted-page lifecycle.
    """
    sb=sb or {}; rep=rep or {}
    user=norm_email(rep.get('bot_user') or sb.get('USER_LOGIN'))
    page_id=norm(rep.get('dtr_page_id') or sb.get('PAGE_ID'))
    fb_id=norm(rep.get('fb_page_id') or sb.get('FB_PAGE_ID'))
    if user and page_id:
        return f'user_page|{user}|{page_id}'
    if fb_id:
        return f'fb|{fb_id}'
    if sb.get('ID'):
        return f"sb|{norm(sb.get('ID'))}"
    return ''

async def fb_page_opens(ctx, fb_page_id):
    if not fb_page_id: return 'ambiguous'
    url=f'https://www.facebook.com/{fb_page_id}'
    try:
        r=await ctx.request.get(url, timeout=20000, headers={'user-agent':'Mozilla/5.0'})
        txt=(await r.text())[:200000]
        low=txt.lower()
        if "this content isn't available right now" in low or "content isn't available" in low or 'go to feed' in low:
            return 'unavailable'
        if r.status in (200,302) and ('facebook' in low) and ('page' in low or 'profile' in low or 'home_icon' in low):
            return 'available'
        return 'ambiguous'
    except Exception:
        return 'ambiguous'

async def sb_get_row(ctx,h,row_id):
    r=await ctx.request.get(f'https://api.jbfdigital.com.br/campaigns/Messenger/{row_id}', headers=h, timeout=120000)
    if r.status != 200:
        return None
    return await r.json()

async def sb_update(ctx,h,row,payload):
    """Update one SB Messenger row.

    update-many persists STATUS/RESTRICTED_UNTIL but silently ignores NOTES.
    The modal's single-row save path persists NOTES via POST /campaigns/Messenger
    when sent with the row's editable fields. Use that route whenever NOTES is
    present; otherwise use update-many for lightweight status/restriction updates.
    """
    row_id=str(row.get('ID'))
    if 'NOTES' in payload:
        current=await sb_get_row(ctx,h,row_id)
        if not current:
            return 404, 'row not found before save'
        allowed=['ID','PUBLISHER_ID','MESSENGER_USER_ID','PAGE_ID','FB_PAGE_ID','PAGE_NAME','UTM_CAMPAIGN','LEADS','STATUS','SOURCE','VERTICAL','COUNTRY','NOTES','HOLDER1','HOLDER2','ADVERTISER','DATE_START','BROADCAST_TEMPLATE_ID','BROADCAST_TIME','BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID','BROADCAST_LAST_SCHEDULE','RESTRICTED_UNTIL']
        # Match the Dash modal save more closely: omit optional null fields
        # instead of sending them as JSON null. Some rows return SB HTTP 500
        # when null fields such as PUBLISHER_ID are included, while UI save works.
        save_payload={k:current.get(k) for k in allowed if current.get(k) is not None}
        notes_value=payload['NOTES']
        rest_payload={k:v for k,v in payload.items() if k!='NOTES'}
        # Save NOTES with the current row status first. Some Blocked rows 500 if
        # NOTES and STATUS=Broadcast are posted together. Also, update-many
        # ignores RESTRICTED_UNTIL=null; the single-row POST route is the proven
        # way to clear a restriction while preserving NOTES.
        save_payload['NOTES']=notes_value
        if rest_payload.get('RESTRICTED_UNTIL', 'not-present') is None:
            save_payload['RESTRICTED_UNTIL']=None
            rest_payload.pop('RESTRICTED_UNTIL', None)
        r=await ctx.request.post('https://api.jbfdigital.com.br/campaigns/Messenger', headers=h, data=json.dumps(save_payload), timeout=120000)
        txt=(await r.text())[:500]
        if r.status not in (200,201):
            return r.status, txt
        if rest_payload:
            upd={**rest_payload,'ids':[row_id]}
            r2=await ctx.request.put('https://api.jbfdigital.com.br/campaigns/Messenger/update-many', headers=h, data=json.dumps(upd), timeout=120000)
            txt2=(await r2.text())[:500]
            if r2.status not in (200,201):
                return r2.status, txt2
            return r2.status, txt2
        return r.status, txt
    if payload.get('RESTRICTED_UNTIL', 'not-present') is None:
        current=await sb_get_row(ctx,h,row_id)
        if not current:
            return 404, 'row not found before clear restriction'
        allowed=['ID','PUBLISHER_ID','MESSENGER_USER_ID','PAGE_ID','FB_PAGE_ID','PAGE_NAME','UTM_CAMPAIGN','LEADS','STATUS','SOURCE','VERTICAL','COUNTRY','NOTES','HOLDER1','HOLDER2','ADVERTISER','DATE_START','BROADCAST_TEMPLATE_ID','BROADCAST_TIME','BROADCAST_CURRENT_MESSAGE_ID','BROADCAST_MESSAGE_ID','BROADCAST_LAST_SCHEDULE','RESTRICTED_UNTIL']
        save_payload={k:current.get(k) for k in allowed if current.get(k) is not None}
        save_payload['RESTRICTED_UNTIL']=None
        r=await ctx.request.post('https://api.jbfdigital.com.br/campaigns/Messenger', headers=h, data=json.dumps(save_payload), timeout=120000)
        return r.status, (await r.text())[:500]
    upd={**payload,'ids':[row_id]}
    r=await ctx.request.put('https://api.jbfdigital.com.br/campaigns/Messenger/update-many', headers=h, data=json.dumps(upd), timeout=120000)
    return r.status, (await r.text())[:500]

def load_state():
    if STATE_PATH.exists(): return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    return {'runs':[], 'mixed_2022':{}}

def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=STATE_PATH.name+'.', dir=str(STATE_PATH.parent))
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(state,f,ensure_ascii=False,indent=2,sort_keys=True); f.write('\n')
    os.replace(tmp, STATE_PATH)

def discord_token():
    token=os.environ.get('DISCORD_BOT_TOKEN','').strip().strip('"').strip("'")
    if token: return token
    env_path=Path('/root/.hermes/profiles/zeus/.env')
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            if line.startswith('DISCORD_BOT_TOKEN='):
                return line.split('=',1)[1].strip().strip('"').strip("'")
    return ''

def truncate_text(value, limit):
    value=str(value or '')
    return value if len(value)<=limit else value[:limit-1]+'…'

def alert_timestamp(summary=None):
    raw=norm((summary or {}).get('finished_at') or (summary or {}).get('started_at'))
    try:
        return datetime.fromisoformat(raw).astimezone(NY).strftime('%Y-%m-%d %H:%M %Z') if raw else datetime.now(NY).strftime('%Y-%m-%d %H:%M %Z')
    except ValueError:
        return datetime.now(NY).strftime('%Y-%m-%d %H:%M %Z')

def site_sort_key(site):
    """Alphabetical by site family, keeping base + finanzas variants adjacent."""
    value=norm(site).lower()
    family=value
    variant=0
    if value.startswith('finanzas.'):
        family=value[len('finanzas.'):]
        variant=1
    elif value.endswith('finanzas'):
        family=value[:-len('finanzas')]
        variant=1
    return family, variant, value

def derive_sites(row):
    row=row or {}
    sites=[]
    for key in ('DOMAIN','domain','SITE','site'):
        value=norm(row.get(key))
        if value: sites.append(value)
    pub=norm(row.get('PUBLISHER_ID') or row.get('publisher_id'))
    if '_' in pub:
        sites.append(pub.split('_',1)[1])
    tmpl=norm(row.get('BROADCAST_TEMPLATE_NAME') or row.get('TEMPLATE_NAME') or row.get('template_name'))
    if tmpl and not sites:
        sites.append(tmpl.split(' - ',1)[0].strip().lower())
    clean=[]
    for s in sites:
        s=re.sub(r'[^A-Za-z0-9._-]+','',s).strip().lower()
        if s and s not in clean:
            clean.append(s)
    return ','.join(sorted(clean,key=site_sort_key)) if clean else '?'

def post_discord(content):
    token=discord_token()
    if not token:
        raise RuntimeError('DISCORD_BOT_TOKEN unavailable')
    if len(content)>2000:
        raise RuntimeError(f'Discord content exceeds 2000 characters: {len(content)}')
    body=json.dumps({'content':content}, ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(
        f'https://discord.com/api/v10/channels/{TARGET_CHANNEL_ID}/messages',
        data=body,
        headers={'Authorization':f'Bot {token}','Content-Type':'application/json','User-Agent':'MGS-Zeus-DTR-Restricted-Sync/1.0'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        payload=json.load(r)
        return {'status':r.status,'message_id':payload.get('id')}

def restriction_alert_row(row):
    codes=row.get('codes') or row.get('codigos') or ''
    if isinstance(codes,list):
        codes=','.join(codes)
    return (
        f"{truncate_text(row.get('page_name') or row.get('nome da pagina'),20):<20} "
        f"{truncate_text(row.get('fb_page_id') or row.get('fb page id'),18):<18} "
        f"{truncate_text(row.get('page_id') or row.get('page id'),8):<8} "
        f"{truncate_text((row.get('bot_user') or row.get('bot user') or '').replace('@gmail.com',''),18):<18} "
        f"{truncate_text(row.get('segurador'),20):<20} "
        f"{truncate_text(row.get('status_sb') or row.get('status sb') or '?',11):<11} "
        f"{truncate_text(codes,13):<13} "
        f"{truncate_text(row.get('restricted_until_time') or row.get('restricted_until') or row.get('data saida'),16)}"
    )

def build_new_restrictions_alerts(rows, summary, limit=1900):
    rows=sorted(rows, key=lambda r: (r.get('restricted_until') or '9999-99-99', r.get('page_name') or '', r.get('bot_user') or ''))
    timestamp=alert_timestamp(summary)
    total=len(rows)
    first_prefix=[
        'PÁGINAS RESTRITAS — NOVAS APLICADAS NA SMART BIDDING',
        f'Atualizado em: {timestamp}',
        'Fonte: último Completed da DigitalTRChat → Smart Bidding',
        f'Novas nesta execução: {total}',
        '',
        'Página               FB Page ID          Page ID   Bot user           Segurador            Status SB   Códigos       Data saída',
        '-------------------- ------------------ -------- ------------------ -------------------- ----------- ------------- ----------------',
    ]
    continuation_prefix=[
        'PÁGINAS RESTRITAS — NOVAS APLICADAS (CONTINUAÇÃO)',
        f'Atualizado em: {timestamp}',
        f'Novas nesta execução: {total}',
        '',
        'Página               FB Page ID          Page ID   Bot user           Segurador            Status SB   Códigos       Data saída',
        '-------------------- ------------------ -------- ------------------ -------------------- ----------- ------------- ----------------',
    ]
    suffix=[
        '',
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
        'AÇÃO EXECUTADA',
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
        '',
        'As páginas restritas acima foram atualizadas com a data de saída na Dash da Smart Bidding.',
    ]
    messages=[]; current=list(first_prefix)
    def render(lines, first):
        content='```\n'+'\n'.join(lines+suffix)+'\n```'
        if first:
            content+='\n\n**Planilha completa:** <'+str(summary.get('sheet') or REPORT_SHEET_URL)+'>'
        return content
    for row in rows:
        line=restriction_alert_row(row)
        candidate=render(current+[line],not messages)
        minimum=len(first_prefix) if not messages else len(continuation_prefix)
        if len(candidate)>limit and len(current)>minimum:
            messages.append(render(current,not messages))
            current=list(continuation_prefix)
        current.append(line)
    messages.append(render(current,not messages))
    return messages

def build_new_restrictions_alert(rows, summary):
    messages=build_new_restrictions_alerts(rows,summary)
    if len(messages)!=1:
        raise RuntimeError(f'new restrictions require {len(messages)} Discord messages; use build_new_restrictions_alerts')
    return messages[0]

def build_no_new_restrictions_alert(summary):
    stats=summary.get('stats') or {}
    lines=[
        'PÁGINAS RESTRITAS — VARREDURA CONCLUÍDA',
        f'Atualizado em: {alert_timestamp(summary)}',
        '',
        'Nenhuma página restrita nova até o momento, comparado com a última varredura concluída.',
        '',
        f"Já restritas na SB no início: {summary.get('sb_active_restricted_start', 0)}",
        f"Páginas DTR no escopo: {stats.get('dtr_pages', 0)}",
        'Novas aplicadas na SB: 0',
    ]
    return '```\n'+'\n'.join(lines)+'\n```\n\n**Planilha completa:** <'+str(summary.get('sheet') or REPORT_SHEET_URL)+'>'

def build_operational_summary_alerts(rows, summary, limit=1900):
    # Discord operational summary remains strictly Broadcast, even though the
    # report Sheet also tracks alertable Campaign/other active restrictions.
    rows=[row for row in rows if norm(row.get('status sb')).lower()=='broadcast']
    page_counts=Counter()
    sites_by_date=defaultdict(set)
    for row in rows:
        date=row.get('data saida') or '?'
        page_counts[date]+=1
        sites_by_date[date].update(site.strip() for site in norm(row.get('sites')).split(',') if site.strip() and site.strip()!='?')
    row_lines=[]
    for date in sorted(page_counts):
        sites=', '.join(sorted(sites_by_date[date],key=site_sort_key))
        row_lines.append(f"{date:<11}  {page_counts[date]:>7}  {sites}")
    timestamp=alert_timestamp(summary)
    first_prefix=[
        'PÁGINAS RESTRITAS — RESUMO OPERACIONAL',
        f'Atualizado em: {timestamp}',
        'Escopo: somente Status SB = Broadcast',
        '',
        f"Broadcast restritas: {summary.get('sheet_broadcast_restricted',len(rows))}",
        f"On-hold ignoradas: {summary.get('sheet_on_hold_excluded',0)}",
        '',
        'Data saída   Páginas  Sites',
        '-----------  -------  --------------------------------------------------',
    ]
    continuation_prefix=[
        'PÁGINAS RESTRITAS — RESUMO OPERACIONAL (CONTINUAÇÃO)',
        f'Atualizado em: {timestamp}',
        '',
        'Data saída   Páginas  Sites',
        '-----------  -------  --------------------------------------------------',
    ]
    messages=[]; current=list(first_prefix)
    for line in row_lines:
        candidate='```\n'+'\n'.join(current+[line])+'\n```'
        if len(candidate)>limit and len(current)>(len(first_prefix) if not messages else len(continuation_prefix)):
            messages.append('```\n'+'\n'.join(current)+'\n```')
            current=list(continuation_prefix)
        current.append(line)
    messages.append('```\n'+'\n'.join(current)+'\n```')
    return messages

def build_exited_restrictions_alerts(rows, summary, limit=1900):
    rows=sorted(rows,key=lambda row:(row.get('data saida') or '9999-99-99',row.get('nome da pagina') or '',row.get('bot user') or ''))
    timestamp=alert_timestamp(summary)
    first_prefix=[
        'PÁGINAS QUE SAÍRAM DA RESTRIÇÃO',
        f'Atualizado em: {timestamp}',
        '',
        'Página               FB Page ID          Page ID   Bot user           Segurador            Status SB   Códigos       Data saída',
        '-------------------- ------------------ -------- ------------------ -------------------- ----------- ------------- ----------------',
    ]
    continuation_prefix=[
        'PÁGINAS QUE SAÍRAM DA RESTRIÇÃO (CONTINUAÇÃO)',
        f'Atualizado em: {timestamp}',
        '',
        'Página               FB Page ID          Page ID   Bot user           Segurador            Status SB   Códigos       Data saída',
        '-------------------- ------------------ -------- ------------------ -------------------- ----------- ------------- ----------------',
    ]
    messages=[]; current=list(first_prefix)
    for row in rows:
        line=restriction_alert_row(row)
        candidate='```\n'+'\n'.join(current+[line])+'\n```'
        if len(candidate)>limit and len(current)>(len(first_prefix) if not messages else len(continuation_prefix)):
            messages.append('```\n'+'\n'.join(current)+'\n```')
            current=list(continuation_prefix)
        current.append(line)
    messages.append('```\n'+'\n'.join(current)+'\n```')
    return messages

def exited_restrictions_from_sheet(removed_rows, fresh_sb_rows, tday):
    live={}
    for row in fresh_sb_rows:
        bot=norm_email(row.get('USER_LOGIN') or row.get('LOGIN')); page_id=norm(row.get('PAGE_ID'))
        if bot and page_id:
            live[f'bot-page:{bot}|{page_id}']=row
        fb=norm(row.get('FB_PAGE_ID'))
        if fb:
            live.setdefault(f'fb:{fb}',row)
    exited=[]
    for old in removed_rows:
        key=report_page_identity(old); current=live.get(key)
        if current and not active_restricted(current,tday):
            exited.append(old)
    return exited

def google_access_token():
    creds=json.loads(GOOGLE_TOKEN_FILE.read_text(encoding='utf-8'))
    body=urllib.parse.urlencode({
        'client_id':creds['client_id'],
        'client_secret':creds['client_secret'],
        'refresh_token':creds['refresh_token'],
        'grant_type':'refresh_token',
    }).encode()
    req=urllib.request.Request(creds.get('token_uri') or 'https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.load(response)['access_token']

def sheets_api(access_token, method, url, data=None):
    body=None
    headers={'Authorization':f'Bearer {access_token}'}
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=UTF-8'
    req=urllib.request.Request(url,method=method,headers=headers,data=body)
    try:
        with urllib.request.urlopen(req,timeout=60) as response:
            raw=response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode('utf-8','replace')[:1200]
        raise RuntimeError(f'Google Sheets HTTP {exc.code}: {detail}') from exc

def sheet_a1_title(title):
    return "'"+str(title).replace("'","''")+"'"

def site_tab_title(site):
    title=re.sub(r'[\\/\?\*\[\]:]+','-',norm(site)).strip().strip("'")
    if not title:
        raise RuntimeError(f'nome de site inválido para aba: {site!r}')
    return title[:100]

def build_report_datasets(rows, page_headers):
    datasets={REPORT_TOTAL_TAB:[page_headers]+[[row.get(header,'') for header in page_headers] for row in rows]}
    title_to_site={}
    grouped=defaultdict(list)
    for row in rows:
        for site in [item.strip() for item in norm(row.get('sites')).split(',') if item.strip() and item.strip()!='?']:
            title=site_tab_title(site)
            previous=title_to_site.setdefault(title,site)
            if previous!=site:
                raise RuntimeError(f'colisão de nomes de abas de site: {previous!r} e {site!r} -> {title!r}')
            grouped[title].append(row)
    for title in sorted(grouped,key=str.lower):
        datasets[title]=[page_headers]+[[row.get(header,'') for header in page_headers] for row in grouped[title]]
    return datasets


def build_summary_dataset(rows, sheet_stats, updated_at=None):
    updated_at=updated_at or datetime.now(NY)
    page_counts=Counter()
    sites_by_date=defaultdict(set)
    for row in rows:
        exit_date=norm(row.get('data saida')) or '?'
        page_counts[exit_date]+=1
        sites_by_date[exit_date].update(
            item.strip() for item in norm(row.get('sites')).split(',')
            if item.strip() and item.strip()!='?'
        )
    values=[
        ['Páginas Restritas — Resumo'],
        ['Atualizado em',updated_at.strftime('%Y-%m-%d %H:%M %Z')],
        [],
        ['Broadcast restritas',int((sheet_stats or {}).get('sheet_broadcast_restricted',0) or 0)],
        ['Outras restritas ativas',int((sheet_stats or {}).get('sheet_other_status_included',0) or 0)],
        ['On-hold ignoradas',int((sheet_stats or {}).get('sheet_on_hold_excluded',0) or 0)],
        [],
        ['Data de Saída','Páginas','Sites'],
    ]
    for exit_date in sorted(page_counts):
        values.append([
            exit_date,
            page_counts[exit_date],
            ', '.join(sorted(sites_by_date[exit_date],key=site_sort_key)),
        ])
    return values

def report_page_identity(row):
    bot_user=norm_email(row.get('bot user'))
    page_id=norm(row.get('page id'))
    if bot_user and page_id:
        return f'bot-page:{bot_user}|{page_id}'
    fb_page_id=norm(row.get('fb page id'))
    if fb_page_id:
        return f'fb:{fb_page_id}'
    raise RuntimeError(f'página sem chave estável para upsert: {row!r}')

def dedupe_report_rows(rows):
    unique={}
    ordered=[]
    exact_duplicates=0
    for row in rows:
        key=report_page_identity(row)
        if key in unique:
            if unique[key]!=row:
                raise RuntimeError(f'chave duplicada com dados conflitantes: {key}')
            exact_duplicates+=1
            continue
        unique[key]=row
        ordered.append(row)
    return ordered,exact_duplicates

def read_report_datasets(access_token, titles):
    if not titles:
        return {}
    base=f'https://sheets.googleapis.com/v4/spreadsheets/{REPORT_SHEET_ID}'
    params=[('ranges',sheet_a1_title(title)+'!A:J') for title in titles]
    params.append(('majorDimension','ROWS'))
    result=sheets_api(access_token,'GET',base+'/values:batchGet?'+urllib.parse.urlencode(params))
    ranges=result.get('valueRanges') or []
    if len(ranges)!=len(titles):
        raise RuntimeError(f'Google Sheets leitura incremental incompleta: {len(ranges)}/{len(titles)} abas')
    return {title:(item.get('values') or []) for title,item in zip(titles,ranges)}

def plan_incremental_report_updates(desired_datasets, existing_datasets, page_headers):
    expected=dict(desired_datasets)
    for title in existing_datasets:
        if title!='Paginas' and title not in expected:
            # Keep a formerly managed site tab, but remove stale/expired rows.
            # Tab deletion remains a separately confirmed Critical Subset action.
            expected[title]=[page_headers]
    updates={title:values for title,values in expected.items() if existing_datasets.get(title)!=values}
    return expected,updates

def ensure_report_tabs(access_token, required_titles):
    """Ensure all managed tabs exist and Resumo is immediately left of Paginas Totais."""
    base=f'https://sheets.googleapis.com/v4/spreadsheets/{REPORT_SHEET_ID}'
    meta=sheets_api(access_token,'GET',base+'?fields=sheets.properties')
    props=[item['properties'] for item in meta.get('sheets',[])]
    by_title={item['title']:item for item in props}
    requests=[]
    if REPORT_TOTAL_TAB not in by_title:
        legacy=by_title.get(REPORT_LEGACY_TOTAL_TAB)
        default=by_title.get('Sheet1')
        if legacy:
            requests.append({'updateSheetProperties':{'properties':{'sheetId':legacy['sheetId'],'title':REPORT_TOTAL_TAB},'fields':'title'}})
        elif default:
            requests.append({'updateSheetProperties':{'properties':{'sheetId':default['sheetId'],'title':REPORT_TOTAL_TAB},'fields':'title'}})
        else:
            requests.append({'addSheet':{'properties':{'title':REPORT_TOTAL_TAB}}})
    if REPORT_SUMMARY_TAB not in by_title:
        requests.append({'addSheet':{'properties':{'title':REPORT_SUMMARY_TAB,'index':0}}})
    for title in required_titles:
        if title not in {REPORT_TOTAL_TAB,REPORT_SUMMARY_TAB} and title not in by_title:
            requests.append({'addSheet':{'properties':{'title':title}}})
    if requests:
        sheets_api(access_token,'POST',base+':batchUpdate',{'requests':requests})
        meta=sheets_api(access_token,'GET',base+'?fields=sheets.properties')
        props=[item['properties'] for item in meta.get('sheets',[])]
        by_title={item['title']:item for item in props}
    if REPORT_SUMMARY_TAB not in by_title or REPORT_TOTAL_TAB not in by_title:
        raise RuntimeError('Google Sheets não contém Resumo e Paginas Totais após criação')
    if by_title[REPORT_SUMMARY_TAB].get('index')+1 != by_title[REPORT_TOTAL_TAB].get('index'):
        sheets_api(access_token,'POST',base+':batchUpdate',{'requests':[
            {'updateSheetProperties':{'properties':{'sheetId':by_title[REPORT_SUMMARY_TAB]['sheetId'],'index':by_title[REPORT_TOTAL_TAB]['index']},'fields':'index'}}
        ]})
        meta=sheets_api(access_token,'GET',base+'?fields=sheets.properties')
        props=[item['properties'] for item in meta.get('sheets',[])]
        by_title={item['title']:item for item in props}
    if by_title[REPORT_SUMMARY_TAB].get('index')+1 != by_title[REPORT_TOTAL_TAB].get('index'):
        raise RuntimeError('Resumo não ficou imediatamente à esquerda de Paginas Totais')
    return by_title

def write_google_sheet(rows):
    access_token=google_access_token()
    page_headers=['link da pagina','nome da pagina','fb page id','page id','bot user','segurador','sites','status sb','codigos','data saida']
    unique_rows,input_duplicates=dedupe_report_rows(rows)
    desired_datasets=build_report_datasets(unique_rows,page_headers)
    tabs=ensure_report_tabs(access_token,list(desired_datasets))
    existing_datasets=read_report_datasets(access_token,list(tabs))
    expected_datasets,updates=plan_incremental_report_updates(desired_datasets,existing_datasets,page_headers)
    base=f'https://sheets.googleapis.com/v4/spreadsheets/{REPORT_SHEET_ID}'

    def keyed_rows(values):
        if not values:
            return {},0
        headers=values[0]
        result={}; duplicates=0
        for values_row in values[1:]:
            row={header:(values_row[index] if index<len(values_row) else '') for index,header in enumerate(headers)}
            key=report_page_identity(row)
            if key in result:
                duplicates+=1
            result[key]=values_row
        return result,duplicates

    old_paginas,existing_duplicates=keyed_rows(existing_datasets.get('Paginas') or [])
    new_paginas,_=keyed_rows(desired_datasets['Paginas'])
    added_keys=set(new_paginas)-set(old_paginas)
    removed_keys=set(old_paginas)-set(new_paginas)
    changed_keys={key for key in set(old_paginas)&set(new_paginas) if old_paginas[key]!=new_paginas[key]}

    if updates:
        sheets_api(access_token,'POST',base+'/values:batchClear',{'ranges':[sheet_a1_title(title)+'!A:Z' for title in updates]})
        resize=[]
        for title,values in updates.items():
            props=tabs[title]
            needed_rows=max(100,len(values)+10)
            needed_cols=max(5,len(values[0]) if values else 1)
            current=props.get('gridProperties') or {}
            if current.get('rowCount',0)<needed_rows or current.get('columnCount',0)<needed_cols:
                resize.append({'updateSheetProperties':{'properties':{'sheetId':props['sheetId'],'gridProperties':{'rowCount':max(current.get('rowCount',0),needed_rows),'columnCount':max(current.get('columnCount',0),needed_cols)}},'fields':'gridProperties.rowCount,gridProperties.columnCount'}})
        if resize:
            sheets_api(access_token,'POST',base+':batchUpdate',{'requests':resize})
        sheets_api(access_token,'POST',base+'/values:batchUpdate',{
            'valueInputOption':'RAW',
            'data':[{'range':sheet_a1_title(title)+'!A1','majorDimension':'ROWS','values':values} for title,values in updates.items()],
        })
        navy={'red':31/255,'green':78/255,'blue':121/255}
        white={'red':1,'green':1,'blue':1}
        column_widths=[300,230,190,100,290,240,220,120,300,130]
        format_requests=[]
        for title,values in updates.items():
            sid=tabs[title]['sheetId']; cols=len(page_headers)
            format_requests.extend([
                {'clearBasicFilter':{'sheetId':sid}},
                {'repeatCell':{'range':{'sheetId':sid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':cols},'cell':{'userEnteredFormat':{'backgroundColor':navy,'textFormat':{'bold':True,'foregroundColor':white},'horizontalAlignment':'CENTER','verticalAlignment':'MIDDLE','wrapStrategy':'CLIP'}},'fields':'userEnteredFormat'}},
                {'updateSheetProperties':{'properties':{'sheetId':sid,'gridProperties':{'frozenRowCount':1}},'fields':'gridProperties.frozenRowCount'}},
            ])
            if len(values)>1:
                format_requests.extend([
                    {'repeatCell':{'range':{'sheetId':sid,'startRowIndex':1,'endRowIndex':len(values),'startColumnIndex':0,'endColumnIndex':cols},'cell':{'userEnteredFormat':{'verticalAlignment':'MIDDLE','wrapStrategy':'CLIP'}},'fields':'userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy'}},
                    {'setBasicFilter':{'filter':{'range':{'sheetId':sid,'startRowIndex':0,'endRowIndex':len(values),'startColumnIndex':0,'endColumnIndex':cols}}}},
                ])
            for index,pixels in enumerate(column_widths):
                format_requests.append({'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':index,'endIndex':index+1},'properties':{'pixelSize':pixels},'fields':'pixelSize'}})
        sheets_api(access_token,'POST',base+':batchUpdate',{'requests':format_requests})

    readback=read_report_datasets(access_token,list(expected_datasets))
    values_read=list(readback.values())
    expected_values=list(expected_datasets.values())
    if values_read!=expected_values:
        counts_read=[len(values) for values in values_read]
        expected_counts=[len(values) for values in expected_values]
        raise RuntimeError(f'Google Sheets readback divergente: rows={counts_read!r} expected_rows={expected_counts!r}')
    duplicate_keys={}
    for title,values in readback.items():
        _,duplicates=keyed_rows(values)
        if duplicates:
            duplicate_keys[title]=duplicates
    if duplicate_keys:
        raise RuntimeError(f'Google Sheets ainda contém chaves duplicadas: {duplicate_keys!r}')
    rows_by_tab={title:max(0,len(values)-1) for title,values in readback.items()}
    updated_tabs=list(updates)
    removed_page_rows=[]
    for key in sorted(removed_keys):
        values_row=old_paginas[key]
        removed_page_rows.append({header:(values_row[index] if index<len(values_row) else '') for index,header in enumerate(page_headers)})
    removed_page_rows.sort(key=lambda row:(row.get('data saida') or '9999-99-99',row.get('nome da pagina') or '',row.get('bot user') or ''))
    return {
        'url':REPORT_SHEET_URL,
        'rows_paginas':rows_by_tab['Paginas'],
        'site_tabs':len(rows_by_tab)-1,
        'rows_by_tab':rows_by_tab,
        'updated_tabs':updated_tabs,
        'updated_site_tabs':[title for title in updated_tabs if title!='Paginas'],
        'unchanged_tabs':len(rows_by_tab)-len(updated_tabs),
        'added_pages':len(added_keys),
        'removed_pages':len(removed_keys),
        'removed_page_rows':removed_page_rows,
        'changed_pages':len(changed_keys),
        'input_duplicates_removed':input_duplicates,
        'existing_duplicates_removed':existing_duplicates,
        'duplicate_keys_after':0,
        'restricted_only':True,
        'incremental_upsert':True,
        'expiry_inclusive':True,
        'readback_ok':True,
    }

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--user', action='append', default=[])
    ap.add_argument('--limit-users', type=int, default=0)
    ap.add_argument('--start-at', default='', help='Resume sorted user list at this bot-user email (inclusive).')
    ap.add_argument('--limit-accounts', type=int, default=0)
    ap.add_argument('--limit-pages', type=int, default=0)
    ap.add_argument('--max-writes', type=int, default=0, help='Canary safety cap for total writes')
    ap.add_argument('--quiet-noop', action='store_true')
    args=ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True); REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S'); tday=today()
    run_log=LOG_DIR/f'dtr-sb-page-health-sync-{stamp}.json'
    summary={'ok':True,'mode':'apply' if args.apply else 'dry-run','started_at':now_iso(),'today':tday,'errors':[],'changes':[],'log':str(run_log),'sheet':REPORT_SHEET_URL}
    p=browser=ctx=None
    try:
        srows=sheet_rows(); step1_scope=build_step1_scope(srows); active=active_users_from_sheet(srows); summary['sheet_active_users']=len(active); summary['sheet_step1_rows']=dict(step1_scope['row_counts']); summary['step1_overrides']=STEP1_ACTIVE_OVERRIDES
        matched, missing, op_errors=discover_dtr_items(set(active)); summary['matched_1p_users']=len(matched); summary['missing_1p_users']=missing; summary['op_errors']=op_errors
        users=sorted(matched)
        if args.user:
            req={norm_email(u) for u in args.user}; users=[u for u in users if u in req]; miss=sorted(req-set(users))
            if miss: summary['errors'].append({'missing_requested_users':miss})
        if args.limit_users: users=users[:args.limit_users]
        if args.start_at:
            start=norm_email(args.start_at)
            users=[u for u in users if u >= start]
        p,browser,ctx,h=await get_sb_context(); pubs,sb_rows=await fetch_sb_rows(ctx,h); summary['sb_rows']=len(sb_rows); summary['sb_publishers']=len(pubs)
        indexes=build_sb_indexes(sb_rows)
        sb_restricted_ids={str(r.get('ID')) for r in sb_rows if norm(r.get('STATUS'))=='Broadcast' and active_restricted(r,tday)}
        sb_restricted_pages_by_user=defaultdict(set)
        for r in sb_rows:
            if norm(r.get('STATUS'))=='Broadcast' and active_restricted(r,tday) and norm(r.get('USER_LOGIN')) and norm(r.get('PAGE_ID')):
                sb_restricted_pages_by_user[norm_email(r.get('USER_LOGIN'))].add(norm(r.get('PAGE_ID')))
        summary['sb_active_restricted_start']=len(sb_restricted_ids)
        state=load_state(); state.setdefault('alerted_restricted_pages', {})
        stats=Counter(); report_rows=[]; backups=[]; alert_rows=[]; restricted_rows=[]; fresh_sb_rows=[]; exited_rows=[]; writes=0
        for user in users:
            print(f"PROGRESS user_start {user}", flush=True)
            scan=await scan_dtr_user(user, matched[user], step1_scope, args.limit_accounts, args.limit_pages, sb_restricted_pages_by_user.get(user, set()))
            print(f"PROGRESS user_done {user} accounts={len(scan.get('accounts') or [])} reports={len(scan.get('reports') or [])} errors={len(scan.get('errors') or [])}", flush=True)
            stats['users_scanned']+=1; stats['dtr_accounts']+=len(scan.get('accounts') or []); stats['dtr_pages']+=sum(a.get('pages',0) for a in scan.get('accounts') or [])
            stats['skipped_already_restricted_sb']+=sum(a.get('skipped_already_restricted',0) for a in scan.get('accounts') or [])
            for a in scan.get('accounts') or []:
                st=a.get('step1_status') or 'UNKNOWN'
                stats[f'step1_{st}'] += 1
                if st != 'VALID_FOR_STEP2':
                    summary.setdefault('step1_inventory_notes',[]).append({'user':user,'segurador':a.get('name'),'status':st,'reason':a.get('step1_reason'),'pages':a.get('pages',0)})
            if scan.get('errors'): summary['errors'].append({'user':user,'errors':scan['errors']})
            sig_counts=Counter(tuple(a.get('signature') or []) for a in (scan.get('accounts') or []) if a.get('signature'))
            repeated_nonempty_signatures=[list(sig) for sig,count in sig_counts.items() if count>1]
            unsafe_context = bool(repeated_nonempty_signatures)
            seen_sb_ids_for_user=set()
            if unsafe_context:
                summary.setdefault('warnings',[]).append({'user':user,'warning':'account_context_repeated_nonempty_signature','repeated_signatures':repeated_nonempty_signatures[:5],'accounts':len(scan.get('accounts') or []),'action':'dedupe_by_unique_sb_row_id'})
                stats['unsafe_context_users'] += 1
            reports = scan.get('reports') or []
            for rep_idx, rep in enumerate(reports, start=1):
                if rep_idx == 1 or rep_idx % 25 == 0 or rep_idx == len(reports):
                    print(f"PROGRESS user_write {user} {rep_idx}/{len(reports)}", flush=True)
                cls=rep['classification']; note=cls.get('note_code') or ''
                status=cls.get('status') or ''; codes=cls.get('codes') or []
                if status=='SENT': stats['sent']+=1
                elif status in {'SEM_COMPLETED','NO_CAMPAIGN_DATA_YET'}: stats['no_campaign_data_yet']+=1
                else: stats['error_pages']+=1
                for c in codes or ([note] if note else []): stats[f'code_{c}']+=1
                sb, merr=match_sb(rep,indexes)
                action=[]; obs=[]; readback_ok=''
                if not sb:
                    stats[merr or 'match_error']+=1; obs.append(merr or 'match_error')
                else:
                    if unsafe_context and norm(sb.get('ID')) in seen_sb_ids_for_user:
                        stats['unsafe_context_duplicate_sb_row_skipped'] += 1
                        obs.append('unsafe_context_duplicate_sb_row_skipped')
                        report_rows.append({'link da pagina':('https://facebook.com/'+(norm(rep.get('fb_page_id')) or norm(sb.get('FB_PAGE_ID')))) if (norm(rep.get('fb_page_id')) or norm(sb.get('FB_PAGE_ID'))) else '', 'nome da pagina':rep.get('page_name'), 'fb page id':norm(rep.get('fb_page_id')) or norm(sb.get('FB_PAGE_ID')), 'page id':norm(rep.get('dtr_page_id')) or norm(sb.get('PAGE_ID')), 'segurador':rep.get('account_name'), 'bot user':rep.get('bot_user'), 'data':rep.get('completed_date'), 'codigo dos erros':note or ('Sem campanha enviada' if status in {'SEM_COMPLETED','NO_CAMPAIGN_DATA_YET'} else 'Sent'), 'sb status antes':norm(sb.get('STATUS')), 'sb restricted antes':date_only(sb.get('RESTRICTED_UNTIL')), 'acao':'', 'readback ok':'skipped', 'observacao':'; '.join(obs)})
                        continue
                    if unsafe_context:
                        seen_sb_ids_for_user.add(norm(sb.get('ID')))
                    before=public_row(sb); backups.append(before)
                    payload={}
                    sb_status = norm(sb.get('STATUS'))
                    # NOTES: every non-Sent result on writable rows. Blocked rows
                    # are diagnosis-only because the cause may be page-level or
                    # segurador/profile access; automatic writes can mask the real
                    # operational state and have returned SB 500 on this class.
                    if status!='SENT' and note:
                        if sb_status == 'Blocked':
                            obs.append('blocked_notes_skipped_pending_diagnosis')
                            stats['blocked_notes_skipped'] += 1
                        elif status in {'SEM_COMPLETED','NO_CAMPAIGN_DATA_YET'} and active_restricted(sb, tday):
                            obs.append('sem_completed_notes_skipped_active_restricted')
                            stats['sem_completed_active_restricted_notes_skipped'] += 1
                        else:
                            new_notes, changed = append_note(sb.get('NOTES'), note)
                            if changed:
                                payload['NOTES']=new_notes; action.append('notes')
                    # Restricted rules.
                    has_2022 = '#2022' in codes
                    is_restricted_start = str(sb.get('ID')) in sb_restricted_ids
                    sb_status = norm(sb.get('STATUS'))
                    if has_2022 and cls.get('restricted_until'):
                        if sb_status == 'On-hold':
                            obs.append('onhold_2022_no_restricted_write')
                            stats['onhold_2022_skipped'] += 1
                        elif sb_status == 'Blocked':
                            fb_status=await fb_page_opens(ctx, norm(sb.get('FB_PAGE_ID')) or norm(rep.get('fb_page_id')))
                            obs.append('fb_'+fb_status); stats[f'blocked_fb_{fb_status}']+=1
                            obs.append('blocked_requires_page_and_segurador_diagnosis')
                            stats['blocked_2022_restricted_skipped'] += 1
                        else:
                            payload['STATUS']='Broadcast'; payload['RESTRICTED_UNTIL']=cls['restricted_until']; action.append('restricted_until')
                        if len(codes)>1:
                            state.setdefault('mixed_2022',{})[str(sb.get('ID'))]={'last_seen':now_iso(),'codes':codes,'restricted_until':cls['restricted_until'],'sb':before,'dtr':rep,'needs_post_expiry_review':True}
                    elif is_restricted_start and status=='SENT':
                        payload['RESTRICTED_UNTIL']=None; action.append('clear_restricted_sent')
                        cleaned_notes, notes_changed = strip_note_codes(payload.get('NOTES', sb.get('NOTES')), DELIVERY_ERROR_NOTE_CODES)
                        if notes_changed:
                            payload['NOTES']=cleaned_notes; action.append('clear_notes_codes')
                    elif is_restricted_start and status not in {'SEM_COMPLETED','NO_CAMPAIGN_DATA_YET'} and not has_2022:
                        payload['RESTRICTED_UNTIL']=None; action.append('clear_restricted_no2022')
                        cleaned_notes, notes_changed = strip_note_codes(payload.get('NOTES', sb.get('NOTES')), ['#2022'])
                        if notes_changed:
                            payload['NOTES']=cleaned_notes; action.append('clear_notes_2022')
                    # Blocked rule: do not restore to Broadcast from public FB URL alone.
                    # A Blocked row may be a dead page OR a fallen segurador/profile
                    # with the page still publicly online. Reactivation requires a
                    # separate dual diagnosis of page availability + operational
                    # segurador/profile access.
                    if sb_status=='Blocked' and not has_2022:
                        fb_status=await fb_page_opens(ctx, norm(sb.get('FB_PAGE_ID')) or norm(rep.get('fb_page_id')))
                        obs.append('fb_'+fb_status); stats[f'blocked_fb_{fb_status}']+=1
                        obs.append('blocked_requires_page_and_segurador_diagnosis')
                    if payload:
                        if args.apply:
                            if args.max_writes and writes>=args.max_writes:
                                obs.append('write_cap_reached')
                            else:
                                st, txt = await sb_update(ctx,h,sb,payload); writes+=1
                                if st not in (200,201):
                                    summary['errors'].append({'update_failed':before,'status':st,'text':txt,'payload':payload}); readback_ok='no'
                                else:
                                    # Fast exact readback; do not refetch all 3,237 rows after every write.
                                    new_sb=await sb_get_row(ctx,h,str(sb.get('ID')))
                                    checks=[]
                                    if new_sb:
                                        if 'NOTES' in payload: checks.append(norm(new_sb.get('NOTES'))==norm(payload['NOTES']))
                                        if 'STATUS' in payload: checks.append(norm(new_sb.get('STATUS'))==norm(payload['STATUS']))
                                        if 'RESTRICTED_UNTIL' in payload: checks.append(date_only(new_sb.get('RESTRICTED_UNTIL'))==date_only(payload['RESTRICTED_UNTIL']))
                                        readback_ok='yes' if all(checks) else 'no'
                                        if readback_ok=='no': summary['errors'].append({'readback_failed':before,'payload':payload,'after':public_row(new_sb)})
                                        elif 'RESTRICTED_UNTIL' in payload and payload.get('RESTRICTED_UNTIL') is None:
                                            ident=restriction_identity(sb, rep)
                                            if ident:
                                                state.setdefault('alerted_restricted_pages', {}).pop(ident, None)
                                        elif has_2022 and 'RESTRICTED_UNTIL' in payload:
                                            ident=restriction_identity(sb, rep)
                                            status_after=norm(new_sb.get('STATUS'))
                                            if status_after != 'Broadcast':
                                                obs.append('restricted_alert_suppressed_non_broadcast')
                                                stats['restricted_alert_suppressed_non_broadcast'] += 1
                                            elif ident and ident in state.get('alerted_restricted_pages', {}):
                                                obs.append('restricted_alert_suppressed_already_mentioned')
                                                stats['restricted_alert_suppressed_already_mentioned'] += 1
                                            else:
                                                alert_rows.append({'page_name':rep.get('page_name'),'fb_page_id':norm(rep.get('fb_page_id')) or norm(sb.get('FB_PAGE_ID')),'page_id':norm(rep.get('dtr_page_id')) or norm(sb.get('PAGE_ID')),'bot_user':rep.get('bot_user'),'segurador':rep.get('account_name'),'sites':derive_sites(new_sb),'status_sb':status_after,'restricted_until':cls.get('restricted_until'),'restricted_until_time':cls.get('restricted_until_time'),'codes':codes,'sb_id':norm(sb.get('ID')),'alert_identity':ident})
                                            if ident and status_after == 'Broadcast':
                                                state.setdefault('alerted_restricted_pages', {})[ident]={'last_seen':now_iso(),'restricted_until':cls.get('restricted_until'),'sb_id':norm(sb.get('ID')),'page_name':rep.get('page_name'),'bot_user':rep.get('bot_user'),'segurador':rep.get('account_name'),'sites':derive_sites(new_sb),'status_sb':status_after}
                                    else:
                                        readback_ok='no'; summary['errors'].append({'readback_get_failed':before,'payload':payload})
                        else:
                            readback_ok='dry-run'
                        stats['planned_or_done_writes']+=1
                report_rows.append({'link da pagina':('https://facebook.com/'+(norm(rep.get('fb_page_id')) or (norm(sb.get('FB_PAGE_ID')) if sb else ''))) if (norm(rep.get('fb_page_id')) or (norm(sb.get('FB_PAGE_ID')) if sb else '')) else '', 'nome da pagina':rep.get('page_name'), 'fb page id':norm(rep.get('fb_page_id')) or (norm(sb.get('FB_PAGE_ID')) if sb else ''), 'page id':norm(rep.get('dtr_page_id')) or (norm(sb.get('PAGE_ID')) if sb else ''), 'segurador':rep.get('account_name'), 'bot user':rep.get('bot_user'), 'data':rep.get('completed_date'), 'codigo dos erros':note or ('Sem campanha enviada' if status in {'SEM_COMPLETED','NO_CAMPAIGN_DATA_YET'} else 'Sent'), 'sb status antes':norm(sb.get('STATUS')) if sb else '', 'sb restricted antes':date_only(sb.get('RESTRICTED_UNTIL')) if sb else '', 'acao':', '.join(action), 'readback ok':readback_ok, 'observacao':'; '.join(obs)})
                if args.apply and args.max_writes and writes>=args.max_writes:
                    break
            if args.apply and args.max_writes and writes>=args.max_writes: break
        summary['stats']=dict(stats); summary['writes']=writes; summary['backup_rows']=len(backups); summary['new_restrictions_alerted']=len(alert_rows); summary['finished_at']=now_iso()
        backup_path=REPORT_DIR/f'dtr-sb-page-health-sync-backup-{stamp}.json'
        backup_path.write_text(json.dumps(backups,ensure_ascii=False,indent=2),encoding='utf-8'); summary['backup']=str(backup_path)
        if args.apply:
            try:
                _, fresh_sb_rows=await fetch_sb_rows(ctx,h)
                restricted_rows, sheet_stats=restricted_sheet_rows(fresh_sb_rows,active,tday)
                summary.update(sheet_stats)
                summary['sheet_update']=write_google_sheet(restricted_rows)
                exited_rows=exited_restrictions_from_sheet((summary['sheet_update'] or {}).get('removed_page_rows') or [],fresh_sb_rows,tday)
                summary['exited_restrictions']=exited_rows
            except Exception as exc:
                summary['errors'].append({'sheet_update_failed':f'{type(exc).__name__}: {exc}'})
        else:
            summary['sheet_update_skipped']='dry-run'
        if args.apply and (alert_rows or not summary['errors']):
            try:
                deliveries=[]
                if alert_rows:
                    first_contents=build_new_restrictions_alerts(alert_rows, summary)
                    summary['discord_alert_kind']='new_restrictions'
                else:
                    first_contents=[build_no_new_restrictions_alert(summary)]
                    summary['discord_alert_kind']='no_new_restrictions'
                for index,content in enumerate(first_contents,start=1):
                    deliveries.append({'kind':f"{summary['discord_alert_kind']}_{index}",'result':post_discord(content)})
                sheet_ok=bool((summary.get('sheet_update') or {}).get('readback_ok'))
                if not summary['errors'] and sheet_ok:
                    for index,content in enumerate(build_operational_summary_alerts(restricted_rows,summary),start=1):
                        deliveries.append({'kind':f'operational_summary_{index}','result':post_discord(content)})
                    if exited_rows:
                        for index,content in enumerate(build_exited_restrictions_alerts(exited_rows,summary),start=1):
                            deliveries.append({'kind':f'exited_restrictions_{index}','result':post_discord(content)})
                summary['discord_deliveries']=deliveries
                summary['discord_alert_http']=(deliveries[0]['result'] or {}).get('status')
            except Exception as exc:
                summary['errors'].append({'discord_alert_failed':f'{type(exc).__name__}: {exc}'})
        state.setdefault('runs',[]).append({'ts':summary['started_at'],'mode':summary['mode'],'stats':summary['stats'],'writes':writes,'log':str(run_log),'sheet':REPORT_SHEET_URL,'sheet_update_ok':bool((summary.get('sheet_update') or {}).get('readback_ok'))})
        save_state(state)
        if summary['errors']: summary['ok']=False
    except Exception as exc:
        summary['ok']=False; summary['errors'].append({'fatal':f'{type(exc).__name__}: {exc}'})
    finally:
        try:
            if browser: await browser.close()
            if p: await p.stop()
        except Exception: pass
    run_log.write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
    if args.quiet_noop and not summary.get('writes') and summary.get('ok'):
        return
    print(json.dumps({k:summary.get(k) for k in ['ok','mode','sheet_active_users','matched_1p_users','sb_rows','sb_active_restricted_start','stats','writes','log','sheet','sheet_update','backup','errors']},ensure_ascii=False,indent=2))
    sys.exit(0 if summary.get('ok') else 2)

if __name__=='__main__': asyncio.run(main())
