#!/usr/bin/env python3
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/root/mgs-agent/work/mgs-quiz-calendar-176/mgs-quiz-carro')
admin = (ROOT / 'includes/class-mgs-quiz-admin.php').read_text(encoding='utf-8')
bootstrap = (ROOT / 'mgs-quiz-carro.php').read_text(encoding='utf-8')

required = {
    'version_header': 'Version:     1.7.6' in bootstrap,
    'version_constant': "MGS_QUIZ_VERSION', '1.7.6'" in bootstrap,
    'form_preserved': 'id="mgsqReportFilters"' in admin,
    'filter_button_preserved': 'Filtrar relatório</button>' in admin,
    'form_lookup': "var form=document.getElementById('mgsqReportFilters')" in admin,
    'request_submit': "form.requestSubmit();" in admin,
    'submit_fallback': "form.submit();" in admin,
}
failed = [name for name, ok in required.items() if not ok]
if failed:
    raise SystemExit('SOURCE_CHECK_FAIL ' + ','.join(failed))

marker = admin.index('id="mgsqDateRangeTrigger"')
script_start = admin.index('<script>', marker) + len('<script>')
script_end = admin.index('</script>', script_start)
calendar_js = admin[script_start:script_end]

fixture = f'''<!doctype html><html><body>
<form id="mgsqReportFilters" method="get">
  <input type="hidden" name="page" value="mgs-quiz-report">
  <input type="hidden" name="from" id="mgsqDateFrom" value="2026-07-13">
  <input type="hidden" name="to" id="mgsqDateTo" value="2026-07-13">
  <select name="gestor"><option value="">Todos</option><option value="G002" selected>G002</option></select>
  <button type="button" id="mgsqDateRangeTrigger" aria-expanded="false"><span id="mgsqDateRangeLabel"></span></button>
  <div id="mgsqDatePopover">
    <button type="button" data-preset="yesterday">Ontem</button>
    <div class="mgsq-calendar-panel" data-calendar-index="0"><span class="mgsq-month-title"></span><div class="mgsq-days"></div></div>
    <div class="mgsq-calendar-panel" data-calendar-index="1"><span class="mgsq-month-title"></span><div class="mgsq-days"></div></div>
    <div id="mgsqDateError"></div><span id="mgsqDateSummary"></span>
    <button type="button" id="mgsqDateCancel">Cancelar</button>
    <button type="button" id="mgsqDateApply">Aplicar</button>
  </div>
  <button type="submit" id="filterReport">Filtrar relatório</button>
</form>
<script>
window.__submits=[];
document.getElementById('mgsqReportFilters').addEventListener('submit',function(e){{
  e.preventDefault();
  window.__submits.push({{
    from:document.getElementById('mgsqDateFrom').value,
    to:document.getElementById('mgsqDateTo').value,
    gestor:this.elements.gestor.value
  }});
}});
</script>
<script>{calendar_js}</script>
</body></html>'''

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(fixture)

        await page.click('#mgsqDateRangeTrigger')
        await page.click('.mgsq-day[data-date="2026-07-12"]')
        await page.click('.mgsq-day[data-date="2026-07-14"]')
        await page.click('#mgsqDateApply')
        await page.wait_for_function('window.__submits.length === 1')
        first = await page.evaluate('window.__submits[0]')
        assert first == {'from': '2026-07-12', 'to': '2026-07-14', 'gestor': 'G002'}, first

        await page.click('#filterReport')
        await page.wait_for_function('window.__submits.length === 2')
        second = await page.evaluate('window.__submits[1]')
        assert second == first, (first, second)

        await page.click('#mgsqDateRangeTrigger')
        await page.click('.mgsq-day[data-date="2026-07-13"]')
        await page.click('#mgsqDateApply')
        await page.wait_for_timeout(100)
        count = await page.evaluate('window.__submits.length')
        assert count == 2, count

        print('REPORT_APPLY_SUBMIT_TEST_OK apply_submits=1 filter_submits=1 incomplete_blocked=1 filters_preserved=1')
        await browser.close()

asyncio.run(main())
