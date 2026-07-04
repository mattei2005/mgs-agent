#!/usr/bin/env python3
"""Detect #2022 Messenger restrictions in DigitalTRChat campaign reports.

Safe default: read-only. Logs into one DTR bot account from 1Password item, scans
recent completed Subscriber Broadcast campaigns, parses #2022 release date/time,
and emits JSON. Optional SB update is handled by separate sb-set-restricted-until.py.
"""
import argparse, asyncio, json, os, re, subprocess, html
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE='https://digitaltrchat.com'
NY=ZoneInfo('America/New_York')
MONTHS_EN={'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}
MONTHS_ES={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12}

def op_field(item, field):
    env=os.environ.copy()
    cmd=['op','item','get',item,'--vault',env.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--fields',field,'--reveal']
    return subprocess.check_output(cmd, env=env, text=True).strip()

def clean_html(s):
    return html.unescape(re.sub(r'<[^>]+>',' ',s or '')).replace('\u202f',' ').replace('\xa0',' ')

def parse_restriction(text, year=None):
    t=clean_html(text)
    if '#2022' not in t and 'temporarily restricted' not in t.lower() and 'restring' not in t.lower():
        return None
    y=year or datetime.now(NY).year
    # EN: until July 22 at 10:56 PM
    m=re.search(r'until\s+([A-Za-z]+)\s+(\d{1,2})\s+at\s+(\d{1,2}):(\d{2})\s*([AP]M)', t, re.I)
    if m:
        mon=MONTHS_EN.get(m.group(1).lower()); day=int(m.group(2)); hh=int(m.group(3)); mm=int(m.group(4)); ap=m.group(5).upper()
        if ap=='PM' and hh!=12: hh+=12
        if ap=='AM' and hh==12: hh=0
        return {'code':'#2022','restricted_until':f'{y:04d}-{mon:02d}-{day:02d}','restricted_until_time':f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}','raw_error':t}
    # ES/PT-ish: hasta el 22 de julio a las 7:23 a. m. / 8:49 a. m.
    m=re.search(r'hasta\s+el\s+(\d{1,2})\s+de\s+([A-Za-záéíóúñ]+)\s+a\s+las\s+(\d{1,2}):(\d{2})\s*([ap])\.??\s*m\.?', t, re.I)
    if m:
        day=int(m.group(1)); mon=MONTHS_ES.get(m.group(2).lower()); hh=int(m.group(3)); mm=int(m.group(4)); ap=m.group(5).lower()
        if ap=='p' and hh!=12: hh+=12
        if ap=='a' and hh==12: hh=0
        return {'code':'#2022','restricted_until':f'{y:04d}-{mon:02d}-{day:02d}','restricted_until_time':f'{y:04d}-{mon:02d}-{day:02d} {hh:02d}:{mm:02d}','raw_error':t}
    return {'code':'#2022','restricted_until':None,'restricted_until_time':None,'raw_error':t}

async def post_json(ctx, url, form, ref):
    r=await ctx.request.post(url, form=form, headers={'X-Requested-With':'XMLHttpRequest','Referer':ref})
    txt=await r.text()
    return json.loads(txt) if txt else {}

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--item', required=True, help='1Password item title/id for DTR account')
    ap.add_argument('--limit-campaigns', type=int, default=25)
    ap.add_argument('--page-name', help='optional DTR page name filter')
    args=ap.parse_args()
    user=op_field(args.item,'username')
    try: pw=op_field(args.item,'credential')
    except subprocess.CalledProcessError: pw=op_field(args.item,'password')
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        ctx=await browser.new_context(viewport={'width':1600,'height':1000})
        page=await ctx.new_page()
        await page.goto(f'{BASE}/home/login', wait_until='domcontentloaded', timeout=60000)
        inputs=page.locator('input:visible')
        await inputs.nth(0).fill(user); await inputs.nth(1).fill(pw)
        await page.locator('button:visible, input[type=submit]:visible').last.click()
        await page.wait_for_timeout(4000)
        url=f'{BASE}/messenger_bot_enhancers/subscriber_broadcast_campaign'
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        csrf=await page.locator('#csrf_token').input_value()
        base={'draw':'1','start':'0','length':str(args.limit_campaigns),'search_page_id':'','search_value':'','search_status':'2','campaign_date_range':'','csrf_token':csrf,'order[0][column]':'12','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
        for i in range(14):
            base[f'columns[{i}][data]']=str(i); base[f'columns[{i}][searchable]']='true'; base[f'columns[{i}][orderable]']='true'; base[f'columns[{i}][search][value]']=''; base[f'columns[{i}][search][regex]']='false'
        camp=await post_json(ctx,url+'_data',base,url)
        found=[]
        for row in camp.get('data',[]):
            action=row[6] if len(row)>6 else ''
            m=re.search(r"cam-id='(\d+)'", action)
            if not m: continue
            cid=m.group(1)
            page_html=row[3] if len(row)>3 else ''
            page_name=clean_html(page_html).strip()
            fb_match=re.search(r'facebook\.com\\?/(\d+)|facebook\.com/(\d+)', page_html)
            fb_id=next((g for g in (fb_match.groups() if fb_match else []) if g), None)
            if args.page_name and args.page_name.lower() not in page_name.lower():
                continue
            params={'draw':'1','start':'0','length':'50','campaign_id':cid,'csrf_token':csrf,'order[0][column]':'3','order[0][dir]':'desc','search[value]':'','search[regex]':'false'}
            for i in range(9):
                params[f'columns[{i}][data]']=str(i); params[f'columns[{i}][searchable]']='true'; params[f'columns[{i}][orderable]']='true'; params[f'columns[{i}][search][value]']=''; params[f'columns[{i}][search][regex]']='false'
            rep=await post_json(ctx,f'{BASE}/messenger_bot_enhancers/campaign_sent_status_data',params,url)
            for rr in rep.get('data',[]):
                raw=' '.join(str(x) for x in rr)
                parsed=parse_restriction(raw)
                if parsed:
                    found.append({'dtr_item':args.item,'campaign_id':cid,'page_name':page_name,'fb_page_id':fb_id, **parsed})
                    break
        print(json.dumps({'ok':True,'item':args.item,'campaigns_scanned':len(camp.get('data',[])),'restrictions_found':found}, ensure_ascii=False, indent=2))
        await browser.close()
if __name__=='__main__': asyncio.run(main())
