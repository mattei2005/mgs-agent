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
    page.get_by_role('button',name='Cadastro domínios',exact=True).click()
    expect(page.locator('#domain-form')).to_be_visible()
    expect(page.locator('#domain-list strong')).to_have_text(sorted(cfg.get('domains',[])))
    if cfg.get('domains'):
        page.get_by_role('button',name='Ver instruções DNS',exact=True).first.click()
        expect(page.locator('#dns-instructions')).to_be_visible()
        expect(page.locator('#dns-record')).to_contain_text('2.25.165.171')
        expect(page.locator('#dns-notice')).to_contain_text('apenas conexões do proxy Cloudflare')
        page.get_by_role('button',name='Verificar',exact=True).first.click()
        first=next(x for x in cfg['domain_checks'] if x['host']==sorted(cfg['domains'])[0])
        expect(page.locator('.domain-status').first).to_contain_text('Verificado' if first['verified'] else 'Pendente',timeout=10000)
        assert ('verified' in page.locator('.domain-status').first.get_attribute('class'))==first['verified']
    page.get_by_role('button',name='Rotas',exact=True).click()
    if cfg.get('route_count',0)==0:
        expect(page.locator('.empty')).to_have_text('Nenhuma rota cadastrada. Comece em Nova rota.')
    else:
        expect(page.locator('#routes .route')).to_have_count(cfg['route_count'])
    page.get_by_role('button',name='Nova rota',exact=True).click()
    assert page.locator('#host').is_visible() and page.locator('#path').is_visible() and page.locator('#destination').is_visible()
    page.get_by_role('button',name='Cancelar',exact=True).click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors
    browser.close()
print(json.dumps({'username':cfg['username'],'public_admin_UI':True,'route_count_confirmed':cfg.get('route_count',0),'domains_confirmed':len(cfg.get('domains',[])),'domain_form_and_DNS':True,'new_route_form':True,'mobile_no_overflow':True,'javascript_errors':0}))
