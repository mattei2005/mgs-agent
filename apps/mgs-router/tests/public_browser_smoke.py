import json,sys,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
    context=browser.new_context(viewport={'width':1280,'height':850})
    context.add_cookies(cfg['cookies'])
    page=context.new_page();errors=[]
    page.on('pageerror',lambda e:errors.append(type(e).__name__))
    response=page.goto(cfg['url']+'/admin',wait_until='networkidle',timeout=45000)
    assert response.status==200
    expect(page.locator('#username')).to_have_text(cfg['username'])
    assert page.get_by_role('button',name='Nova rota',exact=True).is_visible()
    expect(page.locator('.empty')).to_have_text('Nenhuma rota cadastrada. Comece em Nova rota.')
    page.get_by_role('button',name='Nova rota',exact=True).click()
    assert page.locator('#host').is_visible() and page.locator('#path').is_visible() and page.locator('#destination').is_visible()
    page.get_by_role('button',name='Cancelar',exact=True).click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors
    browser.close()
print(json.dumps({'username':cfg['username'],'public_admin_UI':True,'empty_routes_confirmed':True,'new_route_form':True,'mobile_no_overflow':True,'javascript_errors':0}))
