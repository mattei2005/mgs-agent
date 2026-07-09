#!/usr/bin/env python3
import asyncio, importlib.util, json, re, urllib.parse, html
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE=Path('/root/mgs-agent')
OUTDIR=BASE/'reports'; OUTDIR.mkdir(exist_ok=True)
NY=ZoneInfo('America/New_York')
API='https://api.jbfdigital.com.br'
SB_STATE='/tmp/smartbidding_state_headed.json'
DTR_BASE='https://digitaltrchat.com'
SYNC_PATH=BASE/'scripts/dtr-sb-page-health-sync.py'
spec=importlib.util.spec_from_file_location('sync', str(SYNC_PATH))
sync=importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)

DELETE_TARGETS=[
    ('1063903433472026','19337'),
    ('823864334141386','8341'),
    ('380536875150328','1122'),
    ('346856805184271','702'),
    ('352775804588457','499'),
    ('323736617490470','109'),
    ('330353400164437','107'),
    ('334015689799757','106'),
    ('392418553945157','101'),
]
DTR_VERIFY={'fb_page_id':'802843239573486','page_id':'5461','login':'disparoszuout@gmail.com'}

def norm(v): return '' if v is None else str(v).strip()
def low(v): return norm(v).lower()
def clean(v): return html.unescape(re.sub(r'<[^>]+>',' ',str(v or ''))).replace('\xa0',' ').strip()
def parse_page_card_text(txt):
    t=clean(txt); t=re.sub(r'^Analytics\s+','',t).strip()
    m=re.search(r'(?P<fb>\d{12,})\s*\|\s*(?P<pg>\d+)\s*$', t)
    if not m: return None
    left=t[:m.start()].strip()
    em=re.search(r'([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})', left, re.I)
    if em:
        email=em.group(1); name=(left[:em.start()]+' '+left[em.end():]).strip()
    else:
        email=''; name=left
    return {'page_name':re.sub(r'\s+',' ',name).strip(),'page_email':email,'fb_page_id':m.group('fb'),'page_id':m.group('pg'),'raw':txt}

def public_row(r):
    return {k:norm(r.get(k)) for k in ['ID','USER_LOGIN','LOGIN','PROFILE_NAME','PAGE_NAME','PAGE_ID','FB_PAGE_ID','UTM_CAMPAIGN','STATUS','RESTRICTED_UNTIL','COMPANY','DOMAIN','PUBLISHER_ID']}

async def sb_context():
    p=await async_playwright().start()
    browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=SB_STATE, viewport={'width':1600,'height':1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
    page=await ctx.new_page(); headers={}
    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            try: headers.update(await req.all_headers())
            except Exception: pass
    page.on('request', on_req)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(6000)
    body=(await page.locator('body').inner_text(timeout=10000))[:2000]
    if 'BotGuardError' in body or ('Log in' in body and 'Zeus - Agent' not in body):
        raise RuntimeError('SB session not authenticated or BotGuard/login screen')
    h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}
    h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
    return p,browser,ctx,h

async def fetch_sb_pages(ctx,h):
    rc=await ctx.request.get(API+'/company', headers=h, timeout=120000)
    txt=await rc.text()
    if rc.status!=200: raise RuntimeError(f'/company {rc.status}: {txt[:300]}')
    companies=json.loads(txt); pubs=[]; counts=[]
    for c in companies:
        cname=str(c.get('name') or c.get('companyId') or c.get('id') or c.get('slug') or '').strip().lower().replace(' ','-')
        if cname not in ('digital-trust','digital-trust-2'): continue
        cps=[]
        for pub in c.get('publishers') or []:
            pid=pub.get('publisherId')
            if pid: pubs.append(pid); cps.append(pid)
        counts.append({'company':cname,'publishers_all':len(cps)})
    if len(pubs)<56: raise RuntimeError(f'incomplete SB publisher scope {len(pubs)} {counts}')
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    r=await ctx.request.get(API+'/campaigns/Messenger?'+qs, headers=h, timeout=120000)
    txt=await r.text()
    if r.status!=200: raise RuntimeError(f'/campaigns/Messenger {r.status}: {txt[:300]}')
    rows=json.loads(txt)
    if not isinstance(rows,list) or len(rows)<2500: raise RuntimeError(f'incomplete SB pages rows={len(rows) if isinstance(rows,list) else type(rows)}')
    return rows, {'publishers':len(pubs),'company_counts':counts,'rows':len(rows)}

async def delete_sb_targets():
    p,browser,ctx,h=await sb_context()
    try:
        rows,scope=await fetch_sb_pages(ctx,h)
        before_count=len(rows)
        by_pair={}
        for r in rows:
            by_pair.setdefault((norm(r.get('FB_PAGE_ID')), norm(r.get('PAGE_ID'))), []).append(r)
        backup=[]; results=[]; delete_ids=[]
        for fb,pg in DELETE_TARGETS:
            matches=by_pair.get((fb,pg), [])
            item={'fb_page_id':fb,'page_id':pg,'matches':len(matches)}
            if len(matches)!=1:
                item['status']='SKIPPED_MATCH_COUNT'; item['rows']=[public_row(x) for x in matches[:5]]; results.append(item); continue
            r=matches[0]; pr=public_row(r); backup.append(r)
            item['row_before']=pr
            if pr['UTM_CAMPAIGN'] and pr['UTM_CAMPAIGN']!=f'pg_{pg}':
                item['status']='SKIPPED_UTM_MISMATCH'; results.append(item); continue
            sbid=pr['ID']
            if not sbid:
                item['status']='SKIPPED_NO_SB_ID'; results.append(item); continue
            resp=await ctx.request.delete(API+'/campaigns/Messenger/'+urllib.parse.quote(sbid), headers=h, timeout=120000)
            txt=await resp.text()
            item['delete_http']=resp.status; item['delete_body']=txt[:200]
            if resp.status==200 and txt.strip().lower()=='true':
                item['status']='DELETED'; delete_ids.append(sbid)
            else:
                item['status']='DELETE_FAILED'
            results.append(item)
        stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
        backup_path=OUTDIR/f'sb-delete-requested-9-backup-{stamp}.json'
        backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding='utf-8')
        # refetch and validate
        rows_after,scope_after=await fetch_sb_pages(ctx,h)
        remaining_by_pair={}
        remaining_ids={norm(r.get('ID')) for r in rows_after}
        for r in rows_after: remaining_by_pair.setdefault((norm(r.get('FB_PAGE_ID')), norm(r.get('PAGE_ID'))), []).append(r)
        for item in results:
            fb=item['fb_page_id']; pg=item['page_id']
            item['present_after_by_pair']=len(remaining_by_pair.get((fb,pg), []))
            sbid=(item.get('row_before') or {}).get('ID','')
            item['present_after_by_id']=bool(sbid and sbid in remaining_ids)
        return {'scope_before':scope,'scope_after':scope_after,'rows_before':before_count,'rows_after':len(rows_after),'backup_path':str(backup_path),'results':results,'deleted_count':sum(1 for x in results if x.get('status')=='DELETED')}
    finally:
        await browser.close(); await p.stop()

async def dtr_collect_user(username):
    out={'username':username,'login_ok':False,'accounts':[],'matches':[],'pages_total':0,'errors':[]}
    rows=sync.sheet_rows()
    active=set(sync.active_users_from_sheet(rows))
    matched, missing, op_errors=sync.discover_dtr_items(active | {username})
    if username not in matched:
        out['errors'].append({'type':'credential_not_found','missing':missing,'op_errors':op_errors})
        return out
    password=sync.op_password(matched[username])
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(viewport={'width':1600,'height':1000})
        page=await ctx.new_page()
        try:
            await page.goto(DTR_BASE+'/home/login', wait_until='domcontentloaded', timeout=60000)
            inputs=page.locator('input:visible')
            await inputs.nth(0).fill(username); await inputs.nth(1).fill(password)
            await page.locator('button:visible, input[type=submit]:visible').last.click()
            await page.wait_for_timeout(2500)
            await page.goto(DTR_BASE+'/social_accounts/index', wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(1000)
            out['login_ok']=True
            try: csrf=await page.locator('#csrf_token').input_value(timeout=5000)
            except Exception: csrf=''
            accs=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el=>({id:el.getAttribute('data-id')||el.dataset.id||'', name:(el.innerText||el.textContent||'').trim()})).filter(x=>x.id||x.name)""")
            if not accs: accs=[{'id':'','name':'default'}]
            seen=set(); uniq=[]
            for a in accs:
                aid=norm(a.get('id')); name=clean(a.get('name') or '') or 'default'
                if name in {'Rodolfo Mattei','Geizian Pereira'}: continue
                k=aid+'|'+name
                if k not in seen: seen.add(k); uniq.append({'id':aid,'name':name})
            for a in uniq:
                acc={'id':a['id'],'name':a['name'],'pages':0,'matches':[],'errors':[]}
                try:
                    if a['id']:
                        await ctx.request.post(DTR_BASE+'/social_accounts/fb_rx_account_switch', form={'id':a['id'],'csrf_token':csrf}, headers={'X-Requested-With':'XMLHttpRequest','Referer':DTR_BASE+'/social_accounts/index'}, timeout=60000)
                        await page.goto(DTR_BASE+'/social_accounts/index', wait_until='domcontentloaded', timeout=60000)
                        await page.wait_for_timeout(900)
                        try: csrf=await page.locator('#csrf_token').input_value(timeout=5000)
                        except Exception: pass
                    cards=await page.evaluate("""() => Array.from(document.querySelectorAll('.page_list_ul')).map(el => (el.innerText||el.textContent||'').replace(/\\s+/g,' ').trim())""")
                    parsed=[]
                    for txt in cards:
                        row=parse_page_card_text(txt)
                        if row:
                            row.update({'bot_user':username,'account_id':a['id'],'account_name':a['name']})
                            parsed.append(row)
                    acc['pages']=len(parsed); out['pages_total']+=len(parsed)
                    for row in parsed:
                        if row['fb_page_id']==DTR_VERIFY['fb_page_id'] or row['page_id']==DTR_VERIFY['page_id']:
                            acc['matches'].append(row); out['matches'].append(row)
                except Exception as exc:
                    acc['errors'].append(f'{type(exc).__name__}:{exc}')
                out['accounts'].append(acc)
        except Exception as exc:
            out['errors'].append(f'{type(exc).__name__}:{exc}')
        finally:
            await browser.close()
    return out

async def main():
    stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    result={'started_at':datetime.now(NY).isoformat(timespec='seconds'),'delete_targets':DELETE_TARGETS,'dtr_verify':DTR_VERIFY}
    result['sb_delete']=await delete_sb_targets()
    result['dtr_result']=await dtr_collect_user(DTR_VERIFY['login'])
    result['finished_at']=datetime.now(NY).isoformat(timespec='seconds')
    out=OUTDIR/f'sb-delete-and-dtr-verify-{stamp}.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'result_path':str(out),
        'rows_before':result['sb_delete']['rows_before'],
        'rows_after':result['sb_delete']['rows_after'],
        'deleted_count':result['sb_delete']['deleted_count'],
        'delete_status_counts':{s:sum(1 for x in result['sb_delete']['results'] if x.get('status')==s) for s in sorted(set(x.get('status') for x in result['sb_delete']['results']))},
        'dtr_login_ok':result['dtr_result']['login_ok'],
        'dtr_accounts':len(result['dtr_result']['accounts']),
        'dtr_pages_total':result['dtr_result']['pages_total'],
        'dtr_matches':result['dtr_result']['matches'],
    }, ensure_ascii=False, indent=2))

if __name__=='__main__': asyncio.run(main())
