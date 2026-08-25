#!/usr/bin/env python3
import asyncio,json,re
from pathlib import Path
from playwright.async_api import async_playwright
STATE='/root/.local/share/mgs/smartbidding_state_headed.json'
RUN=Path('/root/mgs-agent/work/sb-smart-routing/20260824T210540-0400-newsoun-eggbev-us-cc-es-split')
SPECS=[('newsounfinanzas','ns-f-us-cc-es'),('eggbevfinanzas','eb-f-us-cc-es')]
async def main():
 out={}
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  c=await b.new_context(storage_state=STATE,viewport={'width':1600,'height':1000})
  pg=await c.new_page()
  for slug,prefix in SPECS:
   await pg.goto(f'https://app.smartbiddingdigital.com/company/digital-trust/{slug}/routing',wait_until='networkidle',timeout=90000)
   await pg.wait_for_timeout(3000)
   body=await pg.locator('body').inner_text()
   if 'Log in to Smart Bidding' in body: raise RuntimeError('session expired')
   names=sorted(set(line.strip() for line in body.splitlines() if line.strip().startswith(prefix)))
   path=RUN/f'ui-{slug}.png'; await pg.screenshot(path=str(path),full_page=True)
   out[slug]={'visible_names':names,'visible_count':len(names),'screenshot':str(path)}
  await b.close()
 (RUN/'95-ui-readback.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(out,ensure_ascii=False,indent=2))
asyncio.run(main())
