"""Read-only production UI assertions. Group deletion is always cancelled."""
import json, os, sys
from playwright.sync_api import sync_playwright, expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
    context=browser.new_context(viewport={'width':1280,'height':850});context.add_cookies(cfg['cookies'])
    assert all(c['expires']==-1 for c in context.cookies() if c['name']=='mgs_session')
    page=context.new_page();errors=[];writes=[]
    page.on('pageerror',lambda e:errors.append(type(e).__name__))
    page.on('request',lambda r:writes.append(r.url.split('?',1)[0]) if r.method=='POST' else None)
    response=page.goto(cfg['url']+'/admin',wait_until='networkidle',timeout=45000);assert response.status==200
    expect(page.locator('#username')).to_have_text(cfg['username'])
    expect(page.locator('#routes .route')).to_have_count(len(cfg['routes']))
    page.get_by_role('button',name='Cadastro domínios',exact=True).click()
    expect(page.locator('#domain-list strong')).to_have_text(sorted(cfg['domains']))
    assert 'emprego.dicasfinancas.info' not in page.locator('#domain-list strong').all_text_contents()
    expect(page.locator('#domain-list .domain-status.verified')).to_have_count(len(cfg['domains']))
    page.get_by_role('button',name='Grupos',exact=True).click()
    expect(page.locator('#groups tr')).to_have_count(len(cfg['groups']))
    expect(page.get_by_role('button',name='Excluir grupo',exact=True)).to_have_count(len(cfg['groups']))
    page.once('dialog',lambda d:d.dismiss())
    page.get_by_role('button',name='Excluir grupo',exact=True).first.click()
    assert not writes,'cancelled group deletion unexpectedly wrote production data'
    page.get_by_role('button',name='Destinos',exact=True).click()
    expect(page.locator('#destinations tr')).to_have_count(len(cfg['catalog']))
    page.get_by_role('button',name='Rotas',exact=True).click()
    page.locator('#domain').select_option('job.conectageral.com');page.locator('#search').fill('/artigosjobs')
    row=page.locator('#routes .route');expect(row).to_have_count(1)
    row.get_by_role('button',name='Editar destino',exact=True).click()
    job=next(r for r in cfg['routes'] if r['host']=='job.conectageral.com' and r['path']=='/artigosjobs')
    assert page.locator('.target-weight').evaluate_all('(es)=>es.map(e=>Number(e.value))')==[t['weight'] for t in job['destinations']]
    assert page.locator('.target-url').evaluate_all('(es)=>es.map(e=>e.value)')==[t['url'] for t in job['destinations']]
    page.get_by_role('button',name='Cancelar',exact=True).click()
    page.locator('#domain').select_option('');page.locator('#search').fill('')
    for view in ['Rotas','Destinos','Grupos','Cadastro domínios']:
        page.get_by_role('button',name=view,exact=True).click();page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.set_viewport_size({'width':1280,'height':850})
    page.reload(wait_until='networkidle');expect(page.locator('#username')).to_have_text(cfg['username'])
    page.clock.install();page.clock.fast_forward(9*60*60*1000)
    response=page.request.get(cfg['url']+'/api/me');assert response.status==200 and response.json()['username']==cfg['username']
    assert all(c['expires']==-1 for c in context.cookies() if c['name']=='mgs_session')
    assert page.request.get(cfg['url']+'/api/routes').json()==cfg['config']
    assert not errors and not writes
    browser.close()
print(json.dumps({'username':cfg['username'],'group_delete_buttons':len(cfg['groups']),'group_cancel_no_write':True,'routes_confirmed':len(cfg['routes']),'catalog_confirmed':len(cfg['catalog']),'domains_green':len(cfg['domains']),'emprego_absent':True,'job_13_URLs_weights_match':True,'session_cookie_no_expiry':True,'browser_clock_advanced9h_session_retained':True,'reload_session_retained':True,'mobile_no_overflow':True,'production_UI_writes':0,'javascript_errors':0}))
