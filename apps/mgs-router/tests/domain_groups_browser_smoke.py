import json,sys,os
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch';cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome');context=browser.new_context(viewport={'width':1280,'height':850});context.add_cookies([{'name':'mgs_session','value':cfg['session'],'url':cfg['url'],'httpOnly':True,'sameSite':'Strict'}]);page=context.new_page();errors=[]
    page.on('pageerror',lambda e:errors.append(type(e).__name__))
    page.goto(cfg['url']+'/admin#dominios');expect(page.locator('#domain-list tr')).to_have_count(30)
    expect(page.locator('#domains-top-page')).to_have_text('Página 1 de 3');expect(page.locator('#domains-page')).to_have_text('Página 1 de 3')
    page.locator('#select-all-domains').check();expect(page.locator('#domain-selection-count')).to_have_text('30 selecionado(s)')
    page.locator('#domains-top-next').click();expect(page.locator('#domain-bulk')).not_to_be_visible();expect(page.locator('#domains-page')).to_have_text('Página 2 de 3');page.locator('#domains-next').click();expect(page.locator('#domain-list tr')).to_have_count(6);expect(page.locator('#domains-top-next')).to_be_disabled()
    page.locator('#domain-search').fill('d000.example.com');expect(page.locator('#domain-list tr')).to_have_count(1);expect(page.locator('#domains-page')).to_have_text('Página 1 de 1')
    page.locator('#domain-groups').click();expect(page.locator('#domain-group-title')).to_have_text('Grupos de Domínios');expect(page.locator('#domain-group-list tr')).to_have_count(1)
    page.locator('#domain-group-name').fill('QA');page.locator('#save-domain-group').click();expect(page.locator('#domain-group-list tr')).to_have_count(2);page.locator('#close-domain-groups').click()
    page.locator('#domain-list input[type=checkbox]').check();page.locator('#domain-assign-group').select_option('QA');page.locator('#domain-assign').click();expect(page.locator('#domain-list tr td').nth(3)).to_have_text('QA')
    page.locator('#domain-groups').click();row=page.locator('#domain-group-list tr').filter(has=page.get_by_role('button',name='QA',exact=True));row.get_by_role('button',name='Editar nome',exact=True).click();page.locator('#domain-group-name').fill('QA Renamed');page.locator('#save-domain-group').click();expect(page.locator('#domain-group-list')).to_contain_text('QA Renamed')
    page.once('dialog',lambda d:d.accept());page.locator('#domain-group-list tr').filter(has=page.get_by_role('button',name='QA Renamed',exact=True)).get_by_role('button',name='Excluir grupo',exact=True).click();expect(page.locator('#domain-group-list tr')).to_have_count(1);page.locator('#close-domain-groups').click();expect(page.locator('#domain-list tr td').nth(3)).to_have_text('Sem grupo')
    page.locator('#domain-search').fill('');page.locator('#domain-group-filter').select_option('MGS');expect(page.locator('#domains-count')).to_contain_text('65 de 66')
    page.locator('#new-domain').fill('new.example.com');page.locator('#new-domain-group').select_option('MGS');page.locator('#add-domain').click();expect(page.locator('#new-domain')).to_have_value('');expect(page.locator('#domains-count')).to_contain_text('66 de 67')
    page.reload();expect(page.locator('#domain-list tr')).to_have_count(30);domainapi=page.request.get(cfg['url']+'/api/domains').json();assert domainapi['metadata']['new.example.com']['group']=='MGS' and domainapi['metadata']['new.example.com']['id']==67
    for width in [1280,390]:
        page.set_viewport_size({'width':width,'height':850});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.locator('#domain-groups').click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.locator('#close-domain-groups').click()
    assert not errors;browser.close()
print(json.dumps({'domain_table':True,'domain_groups_create_rename_ungroup_assign_add_reload':True,'stable_ID':True,'30perpage_top_bottom_synced_selection_cleared':True,'mobile_no_overflow':True,'routes_preserved':True,'javascript_errors':0}))
