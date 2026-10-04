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
        with page.expect_response(lambda r:r.url.endswith('/api/domains/check') and r.request.method=='POST') as checked:
            page.get_by_role('button',name='Verificar',exact=True).first.click()
        assert checked.value.status==200
        completed=checked.value.json()
        first=next(x for x in cfg['domain_checks'] if x['host']==sorted(cfg['domains'])[0])
        expect(page.locator('.domain-status').first).to_contain_text('Verificado' if first['verified'] else 'Pendente',timeout=10000)
        assert ('verified' in page.locator('.domain-status').first.get_attribute('class'))==first['verified']
        saved=page.request.get(cfg['url']+'/api/domains').json()['checks'][first['host']]
        assert saved==completed
        page.reload(wait_until='networkidle')
        page.get_by_role('button',name='Cadastro domínios',exact=True).click()
        expect(page.locator('.domain-status').first).to_contain_text('Verificado' if saved['verified'] else 'Pendente')
        expect(page.locator('#domain-list .hint').first).to_contain_text('resultado salvo')
        loaded=page.request.get(cfg['url']+'/api/domains').json()['checks'][first['host']]
        assert loaded==saved
    page.get_by_role('button',name='Rotas',exact=True).click()
    if cfg.get('route_count',0)==0:
        expect(page.locator('.empty')).to_have_text('Nenhuma rota cadastrada. Comece em Nova rota.')
    else:
        expect(page.locator('#routes .route')).to_have_count(cfg['route_count'])
    page.get_by_role('button',name='Destinos',exact=True).click()
    expect(page.locator('#view-destinations')).to_be_visible()
    expect(page.locator('#destinations tr')).to_have_count(len(cfg.get('catalog',[])))
    if cfg.get('catalog'):
        sample=cfg['catalog'][0]
        page.locator('#destination-search').fill(sample['id'])
        matches=[d for d in cfg['catalog'] if sample['id'].lower() in f"{d['name']} {d['url']} {d.get('group','')} {d['id']}".lower()]
        expect(page.locator('#destinations tr')).to_have_count(len(matches))
        exact=page.locator('#destinations tr').filter(has=page.get_by_role('cell',name=sample['id'],exact=True))
        expect(exact.locator('td').nth(1)).to_have_text(sample['name'])
        page.locator('#destination-search').fill('')
    page.get_by_role('button',name='Grupos',exact=True).click()
    expect(page.locator('#groups tr')).to_have_count(len(cfg.get('groups',[])))
    if cfg.get('groups'):
        page.locator('#groups tr').first.get_by_role('button',name='Editar nome',exact=True).click()
        expect(page.locator('#save-group')).to_have_text('Salvar nome')
        expect(page.locator('#group-name')).to_have_value(sorted(cfg['groups'])[0])
        page.get_by_role('button',name='Cancelar edição',exact=True).click()
        expect(page.locator('#save-group')).to_have_text('Criar grupo')
        page.locator('#groups tr').first.get_by_role('button',name='Ver rotas',exact=True).click()
        expect(page.locator('#view-routes')).to_be_visible()
        selected=page.locator('#route-group-filter').input_value()
        expect(page.locator('#routes .route')).to_have_count(sum(r.get('group')==selected for r in cfg.get('routes',[])))
        page.locator('#route-group-filter').select_option('')
    page.get_by_role('button',name='Rotas',exact=True).click()
    page.get_by_role('button',name='Nova rota',exact=True).click()
    expect(page.locator('#destination-picker option')).to_have_count(len(cfg.get('catalog',[]))+1)
    assert page.locator('#host').is_visible() and page.locator('#path').is_visible() and page.locator('#destination').is_visible()
    page.get_by_role('button',name='Cancelar',exact=True).click()
    for view in ['Rotas','Destinos','Grupos','Cadastro domínios']:
        page.get_by_role('button',name=view,exact=True).click()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.set_viewport_size({'width':1280,'height':850})
    page.get_by_role('button',name='Rotas',exact=True).click()
    compatible=[r for r in cfg.get('routes',[]) if r.get('keitaro_query')]
    for sample in [next((r for r in compatible if r.get('relative_weights')),None),next((r for r in compatible if r.get('response_status')),None)]:
        if not sample:continue
        page.locator('#domain').select_option(sample['host'])
        page.locator('#search').fill(sample['path'])
        row=page.locator('#routes .route').filter(has=page.get_by_role('link',name='https://'+sample['host']+sample['path'],exact=True))
        row.get_by_role('button',name='Editar destino',exact=True).click()
        expect(page.locator('#query-notice')).to_contain_text('Modo Keitaro')
        if sample.get('relative_weights'):
            expect(page.locator('#weight-notice')).to_contain_text('sem arredondamento')
            assert page.locator('.target-weight').evaluate_all('(els)=>els.map(e=>Number(e.value))')==[t['weight'] for t in sample['destinations']]
        else:
            expect(row.locator('summary')).to_have_text('Sem destino — HTTP 500 (Keitaro)')
            assert not page.locator('#destination').evaluate('(e)=>e.required')
        page.get_by_role('button',name='Cancelar',exact=True).click()
    page.locator('#domain').select_option('');page.locator('#search').fill('')
    screenshot=Path('/root/.hermes/profiles/zeus/cache/scratch')/('mgs-router-catalog-'+cfg['username']+'.png')
    page.screenshot(path=str(screenshot),full_page=False)
    assert not errors
    browser.close()
print(json.dumps({'username':cfg['username'],'public_admin_UI':True,'route_count_confirmed':cfg.get('route_count',0),'domains_confirmed':len(cfg.get('domains',[])),'domain_form_and_DNS':True,'new_route_form':True,'catalog_count_confirmed':len(cfg.get('catalog',[])),'group_count_confirmed':len(cfg.get('groups',[])),'catalog_navigation_search_group_filter':True,'mobile_no_overflow':True,'javascript_errors':0}))
