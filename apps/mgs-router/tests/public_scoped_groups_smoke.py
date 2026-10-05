"""Public read-only scoped group modal, filters, editors and cancelled deletion QA."""
import json,os,sys
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin);config=cfg['config']
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
    context=browser.new_context(viewport={'width':1280,'height':850});context.add_cookies(cfg['cookies'])
    page=context.new_page();errors=[];writes=[]
    page.on('pageerror',lambda e:errors.append(type(e).__name__))
    page.on('request',lambda r:writes.append(r.url) if r.method=='POST' else None)
    response=page.goto(cfg['url']+'/admin',wait_until='networkidle',timeout=45000);assert response.status==200
    expect(page.locator('#username')).to_have_text(cfg['username'])
    assert page.locator('#nav-groups').count()==0
    counts={}
    for scope,view,groups,filter_id,table,items in [('route_groups','Campanhas','#route-groups','#route-group-filter','#routes .route',config['routes']),('destination_groups','Landing Pages','#destination-groups','#destination-group-filter','#destinations tr',config['catalog'])]:
        page.get_by_role('button',name=view,exact=True).click()
        expect(page.locator(table)).to_have_count(len(items))
        expect(page.locator(filter_id+' option')).to_have_count(len(config[scope])+1)
        for width in [1280,390]:
            page.set_viewport_size({'width':width,'height':850});page.locator(groups).click()
            expect(page.locator('#group-dialog-title')).to_have_text('Grupos de '+view)
            expect(page.locator('#groups tr')).to_have_count(len(config[scope]))
            for g in config[scope]:
                row=page.locator('#groups tr').filter(has=page.get_by_role('button',name=g,exact=True))
                expect(row.locator('td').nth(1)).to_have_text(str(sum(x.get('group')==g for x in items)))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            if width==1280:
                row=page.locator('#groups tr').first
                row.get_by_role('button',name='Editar nome',exact=True).click()
                expect(page.locator('#group-name')).to_have_value(sorted(config[scope])[0])
                page.locator('#cancel-group').click()
                page.once('dialog',lambda d:d.dismiss())
                row.get_by_role('button',name='Excluir grupo',exact=True).click()
            page.keyboard.press('Escape');expect(page.locator('#group-dialog')).not_to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        # Group filter and search compose. Count is derived from real API items.
        selected=next(g for g in config[scope] if any(x.get('group')==g for x in items))
        page.locator(filter_id).select_option(selected)
        expect(page.locator(table)).to_have_count(sum(x.get('group')==selected for x in items))
        page.locator(filter_id).select_option('')
        page.reload(wait_until='networkidle');page.get_by_role('button',name=view,exact=True).click()
        expect(page.locator(table)).to_have_count(len(items))
        counts[scope]=len(config[scope])
    page.set_viewport_size({'width':1280,'height':850})
    page.get_by_role('button',name='Campanhas',exact=True).click();page.locator('#new').click()
    expect(page.locator('#route-group option')).to_have_count(len(config['route_groups'])+1)
    expect(page.locator('#destination-picker option')).to_have_count(len(config['catalog'])+1)
    page.locator('#cancel').click()
    page.get_by_role('button',name='Landing Pages',exact=True).click();page.locator('#new-destination').click()
    expect(page.locator('#catalog-group option')).to_have_count(len(config['destination_groups'])+1);page.locator('#cancel-destination').click()
    page.get_by_role('button',name='Cadastro domínios',exact=True).click()
    expect(page.locator('#domain-list .domain-status.verified')).to_have_count(len(cfg['domains']))
    page.clock.install();page.clock.fast_forward(9*60*60*1000)
    assert page.request.get(cfg['url']+'/api/me').status==200
    assert all(c['expires']==-1 for c in context.cookies() if c['name']=='mgs_session')
    assert page.request.get(cfg['url']+'/api/routes').json()==config
    if config.get('action_schema') == 1:
        assert not any(r.get('disabled') for r in config['routes']) and not any(d.get('disabled') for d in config['catalog'])
        page.get_by_role('button',name='Campanhas',exact=True).click()
        expect(page.locator('input[data-selection="routes"]')).to_have_count(len(config['routes']))
        page.locator('#select-all-routes').check()
        expect(page.locator('#bulk-routes-count')).to_have_text(str(len(config['routes']))+' selecionado(s)')
        for action in ['delete','clone','enable','disable']:
            page.once('dialog',lambda d:d.dismiss())
            page.locator('[data-bulk-scope="routes"][data-bulk-action="'+action+'"]').click()
        page.locator('[data-bulk-scope="routes"][data-bulk-action="clear"]').click()
        positions=page.locator('#routes .actions').first.locator('button').evaluate_all('(es)=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y}})')
        assert positions[1]['x']>positions[0]['x'] and abs(positions[1]['y']-positions[0]['y'])<2
        for view,scope,trigger,groupkey,itemkey in [('Campanhas','routes','#route-groups','route_groups','routes'),('Landing Pages','destinations','#destination-groups','destination_groups','catalog')]:
            page.get_by_role('button',name=view,exact=True).click()
            if scope=='destinations':
                expect(page.locator('input[data-selection="destinations"]')).to_have_count(len(config['catalog']))
                page.locator('#select-all-destinations').check()
                for action in ['clone','enable','disable']:
                    page.once('dialog',lambda d:d.dismiss());page.locator('[data-bulk-scope="destinations"][data-bulk-action="'+action+'"]').click()
                page.locator('[data-bulk-scope="destinations"][data-bulk-action="delete"]').click()
                expect(page.locator('#message')).to_contain_text('Exclusão bloqueada')
                page.locator('[data-bulk-scope="destinations"][data-bulk-action="clear"]').click()
            page.locator(trigger).click()
            name=next(g for g in config[groupkey] if any(x.get('group')==g for x in config[itemkey]))
            row=page.locator('#groups tr').filter(has=page.get_by_role('button',name=name,exact=True))
            row.locator('input[data-selection="groups"]').check()
            expect(page.locator('#bulk-groups-count')).to_have_text('1 selecionado(s)')
            for action in ['delete','clone','enable','disable']:
                page.once('dialog',lambda d:d.dismiss());page.locator('[data-bulk-scope="groups"][data-bulk-action="'+action+'"]').click()
            page.locator('[data-bulk-scope="groups"][data-bulk-action="clear"]').click();page.keyboard.press('Escape')
        assert page.request.get(cfg['url']+'/api/routes').json()==config
    assert not errors and not writes
    browser.close()
print(json.dumps({'username':cfg['username'],'scoped_groups':counts,'modal_counts_filters_edit_cancel_delete_cancel_reload':True,'mobile_no_document_overflow':True,'domain_green':len(cfg['domains']),'session9h_retained':True,'production_UI_writes':0,'bulk_four_actions_selection_cancel_protection':config.get('action_schema')==1,'horizontal_buttons_verified':config.get('action_schema')==1,'javascript_errors':0}))
