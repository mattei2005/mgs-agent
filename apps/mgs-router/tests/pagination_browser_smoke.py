import json,sys,os
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch';cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome');context=browser.new_context(viewport={'width':1280,'height':850});context.add_cookies([{'name':'mgs_session','value':cfg['session'],'url':cfg['url'],'httpOnly':True,'sameSite':'Strict'}]);page=context.new_page();errors=[];writes=[]
    page.on('pageerror',lambda e:errors.append(type(e).__name__));page.on('request',lambda r:writes.append(r.url) if r.method=='POST' else None)
    page.goto(cfg['url']+'/admin');expect(page.locator('#routes .route')).to_have_count(30)
    expect(page.locator('#routes-page')).to_have_text('Página 1 de 3');expect(page.locator('#routes-prev')).to_be_disabled()
    page.locator('#select-all-routes').check();expect(page.locator('#bulk-routes-count')).to_have_text('30 selecionado(s)')
    page.locator('#routes-next').click();expect(page.locator('#routes-page')).to_have_text('Página 2 de 3');expect(page.locator('#routes .route')).to_have_count(30);expect(page.locator('#bulk-routes')).not_to_be_visible()
    page.get_by_role('button',name='Landing Pages',exact=True).click();expect(page.locator('#destinations tr')).to_have_count(30);expect(page.locator('#destinations-page')).to_have_text('Página 1 de 3')
    page.locator('#destinations-next').click();expect(page.locator('#destinations-page')).to_have_text('Página 2 de 3');expect(page.locator('#destinations tr')).to_have_count(30)
    page.get_by_role('button',name='Campanhas',exact=True).click();expect(page.locator('#routes-page')).to_have_text('Página 2 de 3')
    page.locator('#routes-next').click();expect(page.locator('#routes .route')).to_have_count(5);expect(page.locator('#routes-next')).to_be_disabled()
    page.locator('#routes .route').first.get_by_role('button',name='Editar destino',exact=True).click();expect(page.locator('#route-name')).to_have_value('Campaign 060');page.locator('#cancel').click()
    page.locator('#route-group-filter').select_option('Main');expect(page.locator('#routes-page')).to_have_text('Página 1 de 2');expect(page.locator('#routes .route')).to_have_count(30)
    page.locator('#routes-next').click();expect(page.locator('#routes .route')).to_have_count(10)
    page.locator('#route-group-filter').select_option('Other');expect(page.locator('#routes-page')).to_have_text('Página 1 de 1');expect(page.locator('#routes .route')).to_have_count(25)
    page.locator('#search').fill('Campaign 064');expect(page.locator('#routes .route')).to_have_count(1);expect(page.locator('#routes-prev')).to_be_disabled();expect(page.locator('#routes-next')).to_be_disabled()
    page.locator('#search').fill('absent');expect(page.locator('#routes .empty')).to_be_visible();expect(page.locator('#routes-page')).to_have_text('Página 1 de 1')
    page.locator('#search').fill('');page.locator('#route-group-filter').select_option('');expect(page.locator('#routes .route')).to_have_count(30)
    page.get_by_role('button',name='Landing Pages',exact=True).click();expect(page.locator('#destinations-page')).to_have_text('Página 2 de 3');page.locator('#destinations-next').click();expect(page.locator('#destinations tr')).to_have_count(1);expect(page.locator('#destinations-next')).to_be_disabled()
    page.locator('#destination-group-filter').select_option('Main');expect(page.locator('#destinations-page')).to_have_text('Página 1 de 2');page.locator('#destinations-next').click();expect(page.locator('#destinations tr')).to_have_count(5)
    page.locator('#destination-search').fill('Landing 034');expect(page.locator('#destinations tr')).to_have_count(1);expect(page.locator('#destinations-page')).to_have_text('Página 1 de 1')
    page.locator('#destination-search').fill('');page.locator('#destination-group-filter').select_option('');expect(page.locator('#destinations tr')).to_have_count(30)
    for view in ['Campanhas','Landing Pages']:
        page.get_by_role('button',name=view,exact=True).click();page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.set_viewport_size({'width':1280,'height':850})
    page.reload();expect(page.locator('#destinations-page')).to_have_text('Página 1 de 3');expect(page.locator('#destinations tr')).to_have_count(30)
    assert not errors and not writes
    browser.close()
print(json.dumps({'page_size':30,'independent_campaign_LP_pages':True,'last_partial_page_filters_search_reset':True,'selection_visible_page_only':True,'editor_correct_underlying_index':True,'mobile_no_overflow':True,'zero_API_writes':True,'javascript_errors':0}))
