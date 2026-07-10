#!/usr/bin/env python3
import asyncio,json
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
  page=await c.new_page(); await page.goto('https://app.smartbiddingdigital.com/reports/sms',wait_until='domcontentloaded',timeout=120000); await page.wait_for_timeout(12000)
  headers=[x.strip() for x in await page.locator('th').all_inner_texts() if x.strip()]
  body=(await page.locator('body').inner_text())
  labels=[line.strip() for line in body.splitlines() if any(k in line.upper() for k in ('REVENUE','RECEITA','NET REVENUE','LÍQUID'))]
  print(json.dumps({'headers':headers,'revenue_labels':labels[:30]},ensure_ascii=False))
  await b.close()
asyncio.run(main())
