import json,sys,os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Keep Chromium Unix socket paths under Linux's length limit.
os.environ['TMPDIR'] = '/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin)
with sync_playwright() as p:
    chrome=Path('/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
    if not chrome.exists():
        chrome=Path('/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome')
    browser=p.chromium.launch(headless=True,executable_path=str(chrome))
    context=browser.new_context(viewport={'width':1280,'height':850})
    # Synthetic local-test session; no production users or credentials.
    context.add_cookies([{'name':'mgs_session','value':cfg['session'],'url':cfg['url'],'httpOnly':True,'sameSite':'Strict'}])
    page=context.new_page();errors=[]
    page.on('pageerror',lambda error:errors.append(type(error).__name__))
    response=page.goto(cfg['url']+'/admin');assert response.status==200
    page.locator('#new-domain').fill('qa.example.com, sub.qa.example.com')
    page.get_by_role('button',name='Adicionar domínio',exact=True).click()
    expect(page.locator('#dns-instructions')).to_be_visible()
    expect(page.locator('#dns-host')).to_have_text('Domínio: qa.example.com')
    expect(page.locator('#dns-record')).to_contain_text('2.25.165.171')
    expect(page.locator('#domain-list strong')).to_have_text(['qa.example.com','sub.qa.example.com'])
    page.reload()
    expect(page.locator('#domain-list strong')).to_have_text(['qa.example.com','sub.qa.example.com'])
    page.get_by_role('button',name='Ver instruções DNS',exact=True).first.click()
    expect(page.locator('#dns-notice')).to_contain_text('apenas conexões do proxy Cloudflare')
    page.get_by_role('button',name='Nova rota',exact=True).click()
    page.locator('#host').fill('test.wantabrand.invalid')
    page.locator('#path').fill('/qa-route')
    page.locator('#destination').fill('https://wantabrand.com/qa-one')
    page.get_by_role('button',name='Salvar e aplicar',exact=True).click()
    page.get_by_role('button',name='Editar destino',exact=True).wait_for()
    assert page.locator('.destination').inner_text()=='https://wantabrand.com/qa-one'
    page.get_by_role('button',name='Editar destino',exact=True).click()
    assert page.locator('#host').get_attribute('readonly') is not None
    assert page.locator('#path').get_attribute('readonly') is not None
    page.locator('#destination').fill('https://wantabrand.com/qa-two')
    page.get_by_role('button',name='Salvar e aplicar',exact=True).click()
    expect(page.locator('.destination')).to_have_text('https://wantabrand.com/qa-two')
    page.locator('#search').fill('absent')
    assert page.locator('.empty').inner_text()=='Nenhuma rota corresponde ao filtro.'
    page.locator('#search').fill('')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.get_by_role('button',name='Sair',exact=True).click()
    page.wait_for_url('**/login')
    assert page.get_by_role('button',name='Entrar',exact=True).is_visible()
    assert not errors,errors
    browser.close()
print(json.dumps({'browser':'chromium','create_route':True,'edit_destination':True,'filter':True,'mobile_no_horizontal_overflow':True,'logout':True,'javascript_errors':0}))
