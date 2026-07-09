#!/usr/bin/env python3
import asyncio, importlib.util, json, os, re, html, subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
BASE=Path('/root/mgs-agent'); DTR_BASE='https://digitaltrchat.com'; NY=ZoneInfo('America/New_York'); OUT=BASE/'reports'; OUT.mkdir(exist_ok=True)
TARGET_FB='802843239573486'; TARGET_PG='5461'
spec=importlib.util.spec_from_file_location('sync', str(BASE/'scripts/dtr-sb-page-health-sync.py'))
sync=importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
def norm(v): return '' if v is None else str(v).strip()
def clean(v): return html.unescape(re.sub(r'<[^>]+>',' ',str(v or ''))).replace('\xa0',' ').strip()
def op(cmd, timeout=60): return subprocess.check_output(cmd, text=True, env=os.environ.copy(), timeout=timeout).strip()
def parse_page_card_text(txt):
    t=clean(txt); t=re.sub(r'^Analytics\s+','',t).strip()
    m=re.search(r'(?P<fb>\d{12,})\s*\|\s*(?P<pg>\d+)\s*$', t)
    if not m: return None
    left=t[:m.start()].strip(); em=re.search(r'([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})', left, re.I)
    if em: email=em.group(1); name=(left[:em.start()]+' '+left[em.end():]).strip()
    else: email=''; name=left
    return {'page_name':re.sub(r'\s+',' ',name).strip(),'page_email':email,'fb_page_id':m.group('fb'),'page_id':m.group('pg'),'raw':txt}
def all_dtr_items():
    vault=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
    items=json.loads(op(['op','item','list','--vault',vault,'--format','json'], timeout=90))
    out=[]
    for i in items:
        title=i.get('title',''); item_id=i.get('id') or i.get('uuid') or ''
        if 'digitaltrchat' not in title.lower(): continue
        try: u=op(['op','item','get',item_id,'--vault',vault,'--fields','username','--reveal'], timeout=60).lower()
        except Exception: continue
        if '@' in u and item_id: out.append((u,item_id,title))
    seen=set(); uniq=[]
    for u,item,title in sorted(out):
        if u not in seen: seen.add(u); uniq.append((u,item,title))
    return uniq
async def scan_one(username,item_id):
    res={'username':username,'login_ok':False,'accounts':0,'pages':0,'matches':[],'errors':[]}
    try: password=sync.op_password(item_id)
    except Exception as e: res['errors'].append(f'credential:{type(e).__name__}:{e}'); return res
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(viewport={'width':1400,'height':900})
        page=await ctx.new_page()
        try:
            await page.goto(DTR_BASE+'/home/login', wait_until='domcontentloaded', timeout=45000)
            inputs=page.locator('input:visible'); await inputs.nth(0).fill(username); await inputs.nth(1).fill(password)
            await page.locator('button:visible, input[type=submit]:visible').last.click(); await page.wait_for_timeout(1800)
            await page.goto(DTR_BASE+'/social_accounts/index', wait_until='domcontentloaded', timeout=45000); await page.wait_for_timeout(600)
            res['login_ok']=True
            try: csrf=await page.locator('#csrf_token').input_value(timeout=3000)
            except Exception: csrf=''
            accs=await page.evaluate("""() => Array.from(document.querySelectorAll('.account_switch')).map(el=>({id:el.getAttribute('data-id')||el.dataset.id||'', name:(el.innerText||el.textContent||'').trim()})).filter(x=>x.id||x.name)""")
            if not accs: accs=[{'id':'','name':'default'}]
            seen=set(); uniq=[]
            for a in accs:
                aid=norm(a.get('id')); name=clean(a.get('name') or '') or 'default'
                if name in {'Rodolfo Mattei','Geizian Pereira'}: continue
                k=aid+'|'+name
                if k not in seen: seen.add(k); uniq.append({'id':aid,'name':name})
            res['accounts']=len(uniq)
            for a in uniq:
                try:
                    if a['id']:
                        await ctx.request.post(DTR_BASE+'/social_accounts/fb_rx_account_switch', form={'id':a['id'],'csrf_token':csrf}, headers={'X-Requested-With':'XMLHttpRequest','Referer':DTR_BASE+'/social_accounts/index'}, timeout=45000)
                        await page.goto(DTR_BASE+'/social_accounts/index', wait_until='domcontentloaded', timeout=45000); await page.wait_for_timeout(500)
                        try: csrf=await page.locator('#csrf_token').input_value(timeout=3000)
                        except Exception: pass
                    cards=await page.evaluate("""() => Array.from(document.querySelectorAll('.page_list_ul')).map(el => (el.innerText||el.textContent||'').replace(/\\s+/g,' ').trim())""")
                    for txt in cards:
                        row=parse_page_card_text(txt)
                        if row:
                            res['pages']+=1
                            if row['fb_page_id']==TARGET_FB or row['page_id']==TARGET_PG:
                                row.update({'bot_user':username,'account_id':a['id'],'account_name':a['name']}); res['matches'].append(row)
                except Exception as e: res['errors'].append(f"account {a['name']}:{type(e).__name__}:{e}")
        except Exception as e: res['errors'].append(f'login/scan:{type(e).__name__}:{e}')
        finally: await browser.close()
    return res
async def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--start', type=int, default=1); ap.add_argument('--end', type=int, default=0)
    args=ap.parse_args()
    items=all_dtr_items(); stamp=datetime.now(NY).strftime('%Y%m%d-%H%M%S')
    total=len(items); selected=items[args.start-1:args.end or None]
    results=[]; matches=[]
    for offset,(u,item,title) in enumerate(selected,args.start):
        print(f'{offset}/{total} {u}', flush=True)
        r=await scan_one(u,item); results.append(r); matches.extend(r['matches'])
        if matches: break
    out={'started_at':datetime.now(NY).isoformat(timespec='seconds'),'target':{'fb_page_id':TARGET_FB,'page_id':TARGET_PG},'users_scanned':len(results),'total_items':len(items),'matches':matches,'results':results,'finished_at':datetime.now(NY).isoformat(timespec='seconds')}
    path=OUT/f'dtr-full-target-search-802843239573486-5461-{stamp}.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'path':str(path),'users_scanned':len(results),'total_items':len(items),'matches':matches,'login_ok':sum(1 for r in results if r['login_ok']),'pages':sum(r['pages'] for r in results),'errors':sum(len(r['errors']) for r in results)},ensure_ascii=False,indent=2))
asyncio.run(main())
