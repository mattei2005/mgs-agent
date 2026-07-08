#!/usr/bin/env python3
import asyncio, csv, json, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

SHEET_ID = '1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI'
BASE = Path('/root/mgs-agent/work/sheet-phase1-update-20260708')
TABS = [
    (315043175, BASE/'00-resumo-fase1.tsv'),
    (130786795, BASE/'fase1-dtr-sem-sb.tsv'),
    (860481715, BASE/'fase1-sb-sem-dtr-nao-blocked.tsv'),
    (1767381854, BASE/'fase1-login-difere.tsv'),
]

def tsv_dims(path: Path):
    rows=list(csv.reader(path.read_text(encoding='utf-8').splitlines(), delimiter='\t'))
    return len(rows), max((len(r) for r in rows), default=0)

async def update_tab(page, gid, path):
    text = path.read_text(encoding='utf-8')
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={gid}#gid={gid}'
    await page.goto(url, wait_until='domcontentloaded', timeout=120000)
    await page.wait_for_timeout(9000)
    await page.keyboard.press('Escape')
    # Focus the grid/canvas area.
    await page.mouse.click(520, 420)
    await page.wait_for_timeout(400)
    # Clear the whole current worksheet. Double Ctrl+A is the Google Sheets shortcut for whole sheet.
    await page.keyboard.press('Control+A')
    await page.wait_for_timeout(200)
    await page.keyboard.press('Control+A')
    await page.wait_for_timeout(200)
    await page.keyboard.press('Backspace')
    await page.wait_for_timeout(1000)
    # Paste TSV. With whole sheet selected after clear, paste starts at A1.
    await page.evaluate("async (txt) => { await navigator.clipboard.writeText(txt); }", text)
    await page.keyboard.press('Control+V')
    await page.wait_for_timeout(5000)
    # Force save idle.
    await page.keyboard.press('Escape')
    await page.wait_for_timeout(3000)
    return {'gid': gid, 'file': str(path), 'expected_rows': tsv_dims(path)[0], 'expected_cols': tsv_dims(path)[1]}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(
            viewport={'width': 1600, 'height': 1000},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            permissions=['clipboard-read','clipboard-write'],
        )
        page = await ctx.new_page()
        results=[]
        for gid,path in TABS:
            results.append(await update_tab(page, gid, path))
        await browser.close()
    print(json.dumps({'updated': results}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
