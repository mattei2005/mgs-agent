"""Public read-only scoped group modal, filters, editors and cancelled deletion QA."""
import json,os,sys
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin);source_config=cfg['config'];config={**source_config,'catalog':source_config.get('catalog',[]),'routes':source_config.get('routes',[])}
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
        expect(page.locator(table)).to_have_count(min(30,len(items)) if items else 1)
        expect(page.locator(filter_id+' option')).to_have_count(len(config[scope])+1)
        for width in [1280,390]:
            page.set_viewport_size({'width':width,'height':850});page.locator(groups).click()
            expect(page.locator('#group-dialog-title')).to_have_text('Grupos de '+view)
            expect(page.locator('#groups tr')).to_have_count(len(config[scope]) if config[scope] else 1)
            for g in config[scope]:
                row=page.locator('#groups tr').filter(has=page.get_by_role('button',name=g,exact=True))
                expect(row.locator('td').nth(1)).to_have_text(str(sum(x.get('group')==g for x in items)))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            if width==1280 and config[scope]:
                row=page.locator('#groups tr').first
                row.get_by_role('button',name='Editar nome',exact=True).click()
                expect(page.locator('#group-name')).to_have_value(sorted(config[scope])[0])
                page.locator('#cancel-group').click()
                page.once('dialog',lambda d:d.dismiss())
                row.get_by_role('button',name='Excluir grupo',exact=True).click()
            page.keyboard.press('Escape');expect(page.locator('#group-dialog')).not_to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        # Group filter and search compose. Count is derived from real API items.
        selected=next((g for g in config[scope] if any(x.get('group')==g for x in items)),None)
        if selected:
            page.locator(filter_id).select_option(selected)
            expect(page.locator(table)).to_have_count(min(30,sum(x.get('group')==selected for x in items)))
            page.locator(filter_id).select_option('')
        page.reload(wait_until='networkidle');page.get_by_role('button',name=view,exact=True).click()
        expect(page.locator(table)).to_have_count(min(30,len(items)) if items else 1)
        counts[scope]=len(config[scope])
    # Enumerate every real record through 30-item pages and compare exact sets.
    scanned={}
    for view,scope,table,itemkey in [('Campanhas','routes','#routes .route','routes'),('Landing Pages','destinations','#destinations tr','catalog')]:
        page.get_by_role('button',name=view,exact=True).click()
        observed=[]
        while True:
            expect(page.locator('#'+scope+'-top-page')).to_have_text(page.locator('#'+scope+'-page').inner_text())
            assert page.locator('#'+scope+'-top-prev').is_disabled()==page.locator('#'+scope+'-prev').is_disabled()
            assert page.locator('#'+scope+'-top-next').is_disabled()==page.locator('#'+scope+'-next').is_disabled()
            if config[itemkey]:
                assert page.locator(table).count()<=30
                records=page.locator('#routes a.path').evaluate_all('(es)=>es.map(e=>e.href)') if scope=='routes' else page.locator('#destinations input[data-selection="destinations"]').evaluate_all('(es)=>es.map(e=>e.dataset.key)')
                observed.extend(records)
            if page.locator('#'+scope+'-next').is_disabled():break
            page.locator('#'+scope+'-top-next').click()
        expected=['https://'+r['host']+r['path'] for r in config['routes']] if scope=='routes' else [d['id'] for d in config['catalog']]
        assert len(observed)==len(expected) and len(set(observed))==len(expected) and set(observed)==set(expected)
        while page.locator('#'+scope+'-prev').is_enabled():page.locator('#'+scope+'-prev').click()
        scanned[scope]=len(observed)
    page.set_viewport_size({'width':1280,'height':850})
    page.get_by_role('button',name='Campanhas',exact=True).click();page.locator('#new').click()
    expect(page.locator('#route-group option')).to_have_count(len(config['route_groups'])+1)
    expect(page.locator('#destination-picker option')).to_have_count(len(config['catalog'])+1)
    page.locator('#cancel').click()
    page.get_by_role('button',name='Landing Pages',exact=True).click();page.locator('#new-destination').click()
    expect(page.locator('#catalog-group option')).to_have_count(len(config['destination_groups'])+1);page.locator('#cancel-destination').click()
    page.get_by_role('button',name='Cadastro domínios',exact=True).click()
    domainapi=page.request.get(cfg['url']+'/api/domains').json()
    expect(page.locator('#domain-list tr')).to_have_count(min(30,len(cfg['domains'])))
    expect(page.locator('#domain-list .domain-status.verified')).to_have_count(min(30,len(cfg['domains'])))
    if domainapi.get('group_schema')==1:
        assert domainapi['domain_groups']==['MGS'] and all(m['group']=='MGS' for m in domainapi['metadata'].values())
        expect(page.locator('#domain-list tr td:nth-child(4)')).to_have_text(['MGS']*min(30,len(cfg['domains'])))
        page.locator('#domain-groups').click();expect(page.locator('#domain-group-title')).to_have_text('Grupos de Domínios')
        expect(page.locator('#domain-group-list tr td').nth(1)).to_have_text(str(len(cfg['domains'])));page.locator('#close-domain-groups').click()
        page.locator('#domain-search').fill(cfg['domains'][0]);expect(page.locator('#domain-list tr')).to_have_count(1)
        page.locator('#domain-list tr').get_by_role('button',name='Ver instruções DNS',exact=True).click();expect(page.locator('#dns-host')).to_have_text('Domínio: '+cfg['domains'][0])
        page.locator('#domain-search').fill('');page.locator('#domain-group-filter').select_option('MGS');expect(page.locator('#domains-count')).to_contain_text(str(len(cfg['domains']))+' de '+str(len(cfg['domains'])))
        page.locator('#select-all-domains').check();expect(page.locator('#domain-selection-count')).to_have_text(str(min(30,len(cfg['domains'])))+' selecionado(s)');page.locator('#domain-clear').click()
        for width in [1280,390]:
            page.set_viewport_size({'width':width,'height':850});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.set_viewport_size({'width':1280,'height':850})
    assert page.locator('#destinations tr td:first-child span').count()==0
    page.clock.install();page.clock.fast_forward(9*60*60*1000)
    assert page.request.get(cfg['url']+'/api/me').status==200
    assert all(c['expires']==-1 for c in context.cookies() if c['name']=='mgs_session')
    assert page.request.get(cfg['url']+'/api/routes').json()==source_config
    if config.get('action_schema') == 1:
        page.get_by_role('button',name='Campanhas',exact=True).click()
        expect(page.locator('input[data-selection="routes"]')).to_have_count(min(30,len(config['routes'])))
        if config['routes']:
            page.locator('#select-all-routes').check()
            expect(page.locator('#bulk-routes-count')).to_have_text(str(min(30,len(config['routes'])))+' selecionado(s)')
            for action in ['delete','clone','enable','disable']:
                page.once('dialog',lambda d:d.dismiss())
                page.locator('[data-bulk-scope="routes"][data-bulk-action="'+action+'"]').click()
            page.locator('[data-bulk-scope="routes"][data-bulk-action="clear"]').click()
            positions=page.locator('#routes .actions').first.locator('button').evaluate_all('(es)=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y}})')
            assert positions[1]['x']>positions[0]['x'] and abs(positions[1]['y']-positions[0]['y'])<2
        for view,scope,trigger,groupkey,itemkey in [('Campanhas','routes','#route-groups','route_groups','routes'),('Landing Pages','destinations','#destination-groups','destination_groups','catalog')]:
            page.get_by_role('button',name=view,exact=True).click()
            if scope=='destinations' and config['catalog']:
                expect(page.locator('input[data-selection="destinations"]')).to_have_count(min(30,len(config['catalog'])))
                page.locator('#select-all-destinations').check()
                for action in ['clone','enable','disable']:
                    page.once('dialog',lambda d:d.dismiss());page.locator('[data-bulk-scope="destinations"][data-bulk-action="'+action+'"]').click()
                selected_ids=set(page.locator('input[data-selection="destinations"]:checked').evaluate_all('(es)=>es.map(e=>e.dataset.key)'))
                if any(r.get('destination_id') in selected_ids or any(t.get('destination_id') in selected_ids for t in r.get('destinations',[])) for r in config['routes']):
                    page.locator('[data-bulk-scope="destinations"][data-bulk-action="delete"]').click()
                    expect(page.locator('#message')).to_contain_text('Exclusão bloqueada')
                else:
                    page.once('dialog',lambda d:d.dismiss());page.locator('[data-bulk-scope="destinations"][data-bulk-action="delete"]').click()
                page.locator('[data-bulk-scope="destinations"][data-bulk-action="clear"]').click()
            page.locator(trigger).click()
            name=next((g for g in config[groupkey] if any(x.get('group')==g for x in config[itemkey])),None)
            if name is None:
                page.keyboard.press('Escape');continue
            row=page.locator('#groups tr').filter(has=page.get_by_role('button',name=name,exact=True))
            row.locator('input[data-selection="groups"]').check()
            expect(page.locator('#bulk-groups-count')).to_have_text('1 selecionado(s)')
            for action in ['delete','clone','enable','disable']:
                page.once('dialog',lambda d:d.dismiss());page.locator('[data-bulk-scope="groups"][data-bulk-action="'+action+'"]').click()
            page.locator('[data-bulk-scope="groups"][data-bulk-action="clear"]').click();page.keyboard.press('Escape')
        assert page.request.get(cfg['url']+'/api/routes').json()==source_config
    assert not errors and not writes
    browser.close()
print(json.dumps({'username':cfg['username'],'scoped_groups':counts,'modal_counts_filters_edit_cancel_delete_cancel_reload':True,'mobile_no_document_overflow':True,'domain_green':len(cfg['domains']),'session9h_retained':True,'production_UI_writes':0,'bulk_four_actions_selection_cancel_protection':config.get('action_schema')==1,'horizontal_buttons_verified':config.get('action_schema')==1,'page_size':30,'top_bottom_pagination_synced':True,'domain_layout_MGS_group_validated':domainapi.get('group_schema')==1,'landing_ID_column_hidden_internal_refs_preserved':True,'all_pages_exact_records':scanned,'javascript_errors':0}))
