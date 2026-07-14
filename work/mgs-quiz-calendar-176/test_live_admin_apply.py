#!/usr/bin/env python3
import asyncio
import os
import subprocess
from urllib.parse import parse_qs, urlparse
from playwright.async_api import async_playwright

ITEM = 'Wordpress - creditoparaveiculo.com'
VAULT = os.environ.get('OP_DEFAULT_VAULT', 'MGS Conteúdo')

def secret(label):
    p = subprocess.run(
        ['op', 'item', 'get', ITEM, '--vault', VAULT, '--fields', f'label={label}', '--reveal'],
        text=True, capture_output=True, timeout=90,
    )
    value = p.stdout.strip()
    if p.returncode != 0 or not value:
        raise RuntimeError(f'Could not resolve WordPress field: {label}')
    return value

async def main():
    username = secret('username')
    password = secret('password')
    login_url = secret('login_ur')
    report_url = (
        'https://creditoparaveiculo.com/wp-admin/admin.php?page=mgs-quiz-report'
        '&from=2026-07-12&to=2026-07-13&leads_per_page=25'
    )
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1600, 'height': 1000})
        page = await context.new_page()
        await page.goto(login_url, wait_until='domcontentloaded', timeout=120000)
        if await page.locator('#user_login').count():
            await page.fill('#user_login', username)
            await page.fill('#user_pass', password)
            await page.click('#wp-submit')
            await page.wait_for_load_state('domcontentloaded')
        await page.goto(report_url, wait_until='domcontentloaded', timeout=120000)
        if not await page.locator('#mgsqReportFilters').count():
            raise RuntimeError('Authenticated report form not rendered')
        version = await page.evaluate("document.querySelector('script[src*=" + '"quiz.js"' + "]')?.src || ''")
        assert await page.locator('#mgsqDateApply').count() == 1
        assert await page.get_by_role('button', name='Filtrar relatório').count() == 1

        await page.click('#mgsqDateRangeTrigger')
        await page.click('.mgsq-day[data-date="2026-07-13"]')
        await page.click('.mgsq-day[data-date="2026-07-14"]')
        await page.click('#mgsqDateApply')
        await page.wait_for_load_state('domcontentloaded')
        apply_query = parse_qs(urlparse(page.url).query)
        assert apply_query.get('from') == ['2026-07-13'], apply_query
        assert apply_query.get('to') == ['2026-07-14'], apply_query
        assert apply_query.get('leads_per_page') == ['25'], apply_query

        await page.select_option('select[name="leads_per_page"]', '10')
        await page.get_by_role('button', name='Filtrar relatório').click()
        await page.wait_for_load_state('domcontentloaded')
        filter_query = parse_qs(urlparse(page.url).query)
        assert filter_query.get('from') == ['2026-07-13'], filter_query
        assert filter_query.get('to') == ['2026-07-14'], filter_query
        assert filter_query.get('leads_per_page') == ['10'], filter_query

        print('LIVE_ADMIN_REPORT_OK apply_updated_all=1 filter_button_preserved=1 from=2026-07-13 to=2026-07-14 leads_preserved=25 filter_changed_leads=10')
        await browser.close()

asyncio.run(main())
