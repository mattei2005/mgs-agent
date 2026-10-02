import asyncio,json,sys,time
from pathlib import Path
from contextlib import contextmanager
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_browser_budget as budget
from playwright.async_api import async_playwright
cfg,role,kind,hold=sys.argv[1:]; hold=float(hold)
started=time.monotonic()
if kind=='batch': context=budget.scheduled_browser_job(role,config_path=Path(cfg))
else:
 @contextmanager
 def interactive():
  lease=budget.Lease(Path(cfg),batch=False).acquire()
  try:yield lease
  finally:lease.release()
 context=interactive()
async def browser_smoke():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  try:
   page=await browser.new_page()
   await page.set_content('<main id="fixture">'+role+'</main>')
   assert await page.locator('#fixture').inner_text()==role
   await asyncio.sleep(hold)
  finally:await browser.close()
with context as lease:
 admitted=time.monotonic()
 print(json.dumps({'kind':'admitted','role':role,'at':admitted,'slot':lease.slot,'wait_seconds':lease.wait_seconds}),flush=True)
 asyncio.run(browser_smoke())
finished=time.monotonic()
print(json.dumps({'kind':'complete','role':role,'at':finished,'elapsed_seconds':finished-started,'pass':True}),flush=True)
