#!/usr/bin/env python3
import asyncio,json
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state='/tmp/smartbidding_state_headed.json',viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')
  page=await c.new_page(); await page.goto('https://app.smartbiddingdigital.com/reports/sms',wait_until='domcontentloaded',timeout=120000); await page.wait_for_timeout(12000)
  first=page.locator('table tbody tr').first
  cells=first.locator('td'); rev_html=await cells.nth(10).inner_html() if await cells.count()>10 else ''
  controls=[]
  for sel in ('input[type=checkbox]','button[role=switch]','[role=switch]'):
   loc=page.locator(sel)
   for i in range(await loc.count()):
    el=loc.nth(i)
    controls.append({'selector':sel,'checked':await el.is_checked() if await el.get_attribute('type')=='checkbox' else await el.get_attribute('aria-checked'),'outer':(await el.evaluate('(e)=>e.outerHTML'))[:700]})
  body=(await page.locator('body').inner_text()).splitlines()
  context=[]
  for i,line in enumerate(body):
   if 'Discount revenue share' in line:
    context=body[max(0,i-3):i+5]
  print(json.dumps({'revenue_cell_html':rev_html[:3000],'controls':controls[:20],'discount_context':context},ensure_ascii=False))
  await b.close()
asyncio.run(main())
