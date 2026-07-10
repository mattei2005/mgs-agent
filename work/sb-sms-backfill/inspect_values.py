#!/usr/bin/env python3
import asyncio,json
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
  page=await c.new_page(); await page.goto('https://app.smartbiddingdigital.com/reports/sms',wait_until='domcontentloaded',timeout=120000); await page.wait_for_timeout(12000)
  headers=[x.strip() for x in await page.locator('th').all_inner_texts() if x.strip()]
  trs=page.locator('table tbody tr'); rows=[]
  for i in range(min(await trs.count(),3)):
   rows.append([x.strip() for x in await trs.nth(i).locator('td').all_inner_texts()])
  selects=[]
  for i in range(await page.locator('select').count()):
   s=page.locator('select').nth(i)
   selects.append({'value':await s.input_value(),'text':(await s.inner_text())[:400]})
  print(json.dumps({'headers':headers,'rows':rows,'selects':selects},ensure_ascii=False))
  await b.close()
asyncio.run(main())
