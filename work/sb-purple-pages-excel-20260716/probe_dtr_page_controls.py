#!/usr/bin/env python3
import asyncio,json,subprocess
from playwright.async_api import async_playwright
BASE='https://digitaltrchat.com';ITEM='Digitaltrchat - Disparos Helixenit MX-CC-ES'
def fld(x):return subprocess.check_output(['op','item','get',ITEM,'--vault','MGS Conteúdo','--field',x,'--reveal'],text=True).strip()
async def main():
 u=fld('username')
 try:pwd=fld('credential')
 except subprocess.CalledProcessError:pwd=fld('password')
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,args=['--no-sandbox']);ctx=await browser.new_context();page=await ctx.new_page()
  await page.goto(BASE+'/home/login');ins=page.locator('input:visible');await ins.nth(0).fill(u);await ins.nth(1).fill(pwd);await page.locator('button:visible,input[type=submit]:visible').last.click();await page.wait_for_timeout(3500)
  ref=BASE+'/messenger_bot_enhancers/subscriber_broadcast_campaign';await page.goto(ref);await page.wait_for_timeout(700);csrf=await page.locator('#csrf_token').input_value()
  accs=await page.evaluate("""()=>Array.from(document.querySelectorAll('.account_switch')).map(e=>({id:e.dataset.id||e.getAttribute('data-id'),name:(e.innerText||'').trim()}))""");acc={x['id']:x for x in accs if 'Vivian Silva' in x['name']};a=next(iter(acc.values()))
  await ctx.request.post(BASE+'/social_accounts/fb_rx_account_switch',form={'id':a['id'],'csrf_token':csrf},headers={'X-Requested-With':'XMLHttpRequest','Referer':ref});await page.goto(BASE+'/social_accounts/index');await page.wait_for_timeout(700)
  data=await page.evaluate(r"""()=>Array.from(document.querySelectorAll('.page_list_ul')).map(el=>({text:(el.innerText||'').replace(/\s+/g,' ').trim(),links:Array.from(el.querySelectorAll('a')).map(a=>({text:(a.innerText||a.title||'').trim(),href:a.getAttribute('href'),onclick:a.getAttribute('onclick'),cls:a.className,data:Object.fromEntries(Array.from(a.attributes).filter(x=>x.name.startsWith('data-')).map(x=>[x.name,x.value]))})),buttons:Array.from(el.querySelectorAll('button')).map(a=>({text:(a.innerText||a.title||'').trim(),onclick:a.getAttribute('onclick'),cls:a.className,data:Object.fromEntries(Array.from(a.attributes).filter(x=>x.name.startsWith('data-')).map(x=>[x.name,x.value]))}))}))""")
  print(json.dumps(data,ensure_ascii=False,indent=2));await browser.close()
asyncio.run(main())
