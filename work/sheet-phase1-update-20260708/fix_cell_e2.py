#!/usr/bin/env python3
import asyncio, json
from playwright.async_api import async_playwright
SHEET_ID='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
  ctx=await b.new_context(viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',permissions=['clipboard-read','clipboard-write'])
  page=await ctx.new_page(); await page.goto(f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid=860481715#gid=860481715',wait_until='domcontentloaded',timeout=120000); await page.wait_for_timeout(8000)
  # use name box to select E2
  nb=page.locator('input').first()
  await nb.click(); await page.keyboard.press('Control+A'); await page.keyboard.type('E2'); await page.keyboard.press('Enter'); await page.wait_for_timeout(500)
  await page.evaluate("async txt => navigator.clipboard.writeText(txt)", "'1063903433472026")
  await page.keyboard.press('Control+V'); await page.wait_for_timeout(3000)
  await b.close()
 print(json.dumps({'cell':'E2','value':'1063903433472026'}))
asyncio.run(main())
