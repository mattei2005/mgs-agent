#!/usr/bin/env python3
import asyncio, csv, json
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
SHEET_ID='1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
GID=315043175
PATH=Path('/root/mgs-agent/work/sheet-phase1-update-20260708/00-resumo-fase1.tsv')
async def try_click(locator, label):
    try:
        await locator.click(timeout=3000)
        return label+':ok'
    except Exception as e:
        return label+':fail:'+type(e).__name__
async def main():
    text=PATH.read_text(encoding='utf-8')
    logs=[]
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=False,args=['--disable-blink-features=AutomationControlled'])
        ctx=await b.new_context(viewport={'width':1600,'height':1000},user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',permissions=['clipboard-read','clipboard-write'])
        page=await ctx.new_page()
        await page.goto(f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}#gid={GID}',wait_until='domcontentloaded',timeout=120000)
        await page.wait_for_timeout(9000)
        await page.keyboard.press('Escape')
        await page.mouse.click(520,420)
        await page.keyboard.press('Control+A'); await page.wait_for_timeout(200); await page.keyboard.press('Control+A'); await page.wait_for_timeout(500)
        logs.append(await try_click(page.get_by_role('menuitem', name='Format'), 'format-menu'))
        await page.wait_for_timeout(500)
        logs.append(await try_click(page.get_by_text('Merge cells', exact=True), 'merge-cells'))
        await page.wait_for_timeout(500)
        # menu item can be Unmerge or Unmerge cells
        ok=False
        for name in ['Unmerge', 'Unmerge cells']:
            try:
                await page.get_by_text(name, exact=True).click(timeout=2000); logs.append('unmerge:'+name+':ok'); ok=True; break
            except Exception as e:
                logs.append('unmerge:'+name+':fail')
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(500)
        await page.keyboard.press('Control+A'); await page.wait_for_timeout(200); await page.keyboard.press('Control+A')
        await page.keyboard.press('Backspace')
        await page.wait_for_timeout(1000)
        await page.evaluate('async txt => { await navigator.clipboard.writeText(txt); }', text)
        await page.keyboard.press('Control+V')
        await page.wait_for_timeout(6000)
        await b.close()
    print(json.dumps({'logs':logs,'expected_rows':len(list(csv.reader(text.splitlines(),delimiter='\t')))},ensure_ascii=False,indent=2))
asyncio.run(main())
