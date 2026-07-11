#!/usr/bin/env python3
"""SmartBidding Messenger Page Restricted Until updater.

Reads live SB rows and can update RESTRICTED_UNTIL for one Messenger Page row by ID.
Default is dry-run; pass --apply to write. Used by restricted-pages monitor after
DTR detects a real restriction end timestamp.
"""
import argparse, asyncio, json, urllib.parse, tempfile, os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

SB_STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
NY=ZoneInfo('America/New_York')

def norm(v): return '' if v is None else str(v).strip()

def date_only(v): return norm(v)[:10]

async def get_auth_context():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    ctx = await browser.new_context(storage_state=SB_STATE, viewport={'width':1600,'height':1000}, user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
    page = await ctx.new_page(); headers={}
    async def on_req(req):
        if 'api.jbfdigital.com.br' in req.url:
            headers.update(await req.all_headers())
    page.on('request', on_req)
    await page.goto('https://app.smartbiddingdigital.com/accounts', wait_until='domcontentloaded', timeout=60000)
    await page.wait_for_timeout(4000)
    h={k:v for k,v in headers.items() if k.lower() in {'authorization','accept','content-type'}}
    h.update({'origin':'https://app.smartbiddingdigital.com','referer':'https://app.smartbiddingdigital.com/'})
    return p,browser,ctx,h

async def fetch_rows(ctx,h):
    rc=await ctx.request.get('https://api.jbfdigital.com.br/company', headers=h, timeout=120000)
    companies=await rc.json(); pubs=[]
    for company in companies:
        for pub in company.get('publishers') or []:
            if pub.get('active') and pub.get('publisherId'):
                pubs.append(pub['publisherId'])
    qs='&'.join('companies[]='+urllib.parse.quote(x) for x in pubs)+'&source=Messenger'
    r=await ctx.request.get('https://api.jbfdigital.com.br/campaigns/Messenger?'+qs, headers=h, timeout=120000)
    rows=await r.json()
    if r.status != 200 or not isinstance(rows, list):
        raise RuntimeError(f'bad campaigns response status={r.status}')
    return pubs, rows

async def get_account(ctx,h,row_id):
    r=await ctx.request.get(f'https://api.jbfdigital.com.br/accounts/Messenger/{row_id}', headers=h, timeout=120000)
    text=await r.text()
    try: data=json.loads(text)
    except Exception: data=text
    return r.status, data

async def post_account(ctx,h,payload):
    r=await ctx.request.post('https://api.jbfdigital.com.br/accounts/Messenger', headers=h, data=payload, timeout=120000)
    text=await r.text()
    try: data=json.loads(text)
    except Exception: data=text
    return r.status, data

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--page-id', required=True, help='SB row PAGE_ID')
    ap.add_argument('--restricted-until', required=True, help='YYYY-MM-DD or YYYY-MM-DD HH:MM; SB stores date part')
    ap.add_argument('--apply', action='store_true')
    args=ap.parse_args()
    target_date=date_only(args.restricted_until)
    if len(target_date)!=10:
        raise SystemExit('restricted-until must contain YYYY-MM-DD')
    p=browser=ctx=None
    try:
        p,browser,ctx,h=await get_auth_context()
        pubs,rows=await fetch_rows(ctx,h)
        matches=[r for r in rows if norm(r.get('PAGE_ID'))==norm(args.page_id) or norm(r.get('ID'))==norm(args.page_id)]
        if not matches:
            raise SystemExit(json.dumps({'ok':False,'error':'row_not_found','page_id':args.page_id}, ensure_ascii=False))
        row=matches[0]
        before=date_only(row.get('RESTRICTED_UNTIL'))
        payload=dict(row)
        payload['RESTRICTED_UNTIL']=target_date
        result={'ok':True,'dry_run':not args.apply,'id':row.get('ID'),'page_id':row.get('PAGE_ID'),'fb_page_id':row.get('FB_PAGE_ID'),'page_name':row.get('PAGE_NAME'),'before':before,'after':target_date}
        if args.apply:
            status,data=await post_account(ctx,h,payload)
            result['post_status']=status
            result['post_response_type']=type(data).__name__
            # read back live
            _, rows2 = await fetch_rows(ctx,h)
            rb=[r for r in rows2 if norm(r.get('ID'))==norm(row.get('ID'))]
            result['readback_restricted_until']=date_only(rb[0].get('RESTRICTED_UNTIL')) if rb else None
            result['validated']=result['readback_restricted_until']==target_date
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if browser: await browser.close()
        if p: await p.stop()
if __name__=='__main__': asyncio.run(main())
