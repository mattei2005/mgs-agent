#!/usr/bin/env python3
import asyncio, json
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
TARGET='https://app.smartbiddingdigital.com/company/digital-trust/financeadx/routing'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
NAME='fax-us-emp-es-drip 001'

def clean(s): return ' '.join(str(s or '').split())

async def describe(page):
    dialogs=page.locator('[role="dialog"]:visible,.p-dialog:visible,.modal:visible')
    out={'dialogs':await dialogs.count(),'dialog_texts':[],'inputs':[],'buttons':[]}
    for i in range(await dialogs.count()):
        d=dialogs.nth(i); out['dialog_texts'].append(clean(await d.inner_text())[:1800])
    for i in range(await page.locator('input:visible').count()):
        el=page.locator('input:visible').nth(i)
        out['inputs'].append({'type':await el.get_attribute('type'),'placeholder':await el.get_attribute('placeholder'),'value':await el.input_value()})
    for i in range(await page.locator('button:visible').count()):
        b=page.locator('button:visible').nth(i)
        out['buttons'].append({'text':clean(await b.inner_text()),'title':await b.get_attribute('title'),'aria':await b.get_attribute('aria-label')})
    return out

async def main():
    events=[]; p=await async_playwright().start(); browser=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
    ctx=await browser.new_context(storage_state=STATE,viewport={'width':1600,'height':1000},user_agent=UA); page=await ctx.new_page()
    async def resp(r):
        if 'api.jbfdigital.com.br' in r.url:
            u=urlsplit(r.url); events.append({'method':r.request.method,'path':u.path,'query':u.query,'status':r.status})
    page.on('response',resp)
    try:
        await page.goto(TARGET,wait_until='networkidle',timeout=90000); await page.wait_for_timeout(2000)
        loc=page.get_by_text(NAME,exact=True)
        if not await loc.count():
            search=page.locator('input.p-inputtext:visible')
            if not await search.count():
                await page.locator('button:has(.pi-search)').first.click(); await page.wait_for_timeout(300); search=page.locator('input.p-inputtext:visible')
            await search.last.fill(NAME); await search.last.press('Enter'); await page.wait_for_timeout(700); loc=page.get_by_text(NAME,exact=True)
        if not await loc.count(): raise RuntimeError('pool row not found')
        row=loc.first.locator('xpath=ancestor::tr')
        row_info={'text':clean(await row.inner_text()),'buttons':await row.locator('button').count()}
        for i in range(await row.locator('button').count()):
            b=row.locator('button').nth(i); row_info[f'button_{i}']={'text':clean(await b.inner_text()),'title':await b.get_attribute('title'),'aria':await b.get_attribute('aria-label')}
        await row.locator('button').first.click(timeout=10000); await page.wait_for_timeout(1000)
        state1=await describe(page)
        print(json.dumps({'title':await page.title(),'row':row_info,'after_pool_edit':state1,'events':events[-20:]},ensure_ascii=False,indent=2))
    finally:
        await browser.close(); await p.stop()
if __name__=='__main__': asyncio.run(main())
