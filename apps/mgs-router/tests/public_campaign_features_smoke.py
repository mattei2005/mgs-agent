"""Read-only real HTTPS UX: no campaign configuration writes or traffic GETs."""
import json,sys,os
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch';cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome');context=browser.new_context(viewport={'width':1280,'height':850});context.add_cookies(cfg['cookies']);page=context.new_page();errors=[];writes=[]
    page.on('pageerror',lambda e:errors.append(type(e).__name__));page.on('request',lambda r:writes.append(r.url) if r.method=='POST' else None)
    page.goto(cfg['url']+'/admin#rotas',wait_until='networkidle');expect(page.locator('#username')).to_have_text(cfg['username']);expect(page.locator('#sort-clicks')).to_be_visible();expect(page.locator('#click-range')).to_have_value('today')
    tested=[]
    for n in [20,23]:
        r=next(r for r in cfg['config']['routes'] if len(r.get('destinations',[]))==n)
        page.locator('#search').fill(r['host']+r['path']);expect(page.locator('#routes tr.route')).to_have_count(1);page.locator('#routes .text-link').first.click()
        original=page.locator('.target-weight').evaluate_all('(es)=>es.map(e=>Number(e.value))');assert original==[t['weight'] for t in r['destinations']]
        page.locator('#equal-weights').click();weights=page.locator('.target-weight').evaluate_all('(es)=>es.map(e=>Number(e.value))');assert len(weights)==n and len(set(weights))==1 and abs(weights[0]-100/n)<1e-10
        expect(page.locator('#weight-notice')).to_contain_text('Salvar e aplicar');page.locator('#nav-routes').click();expect(page.locator('#editor')).not_to_be_visible();expect(page.locator('#search')).to_have_value(r['host']+r['path'])
        page.locator('#routes .text-link').first.click();assert page.locator('.target-weight').evaluate_all('(es)=>es.map(e=>Number(e.value))')==original;page.locator('#nav-routes').click();tested.append({'destinations':n,'percent':weights[0],'saved':False})
    page.locator('#search').fill('');page.locator('#click-range').select_option('all');page.wait_for_load_state('networkidle');expect(page.locator('#click-period-notice')).to_contain_text('America/New_York')
    assert page.locator('#routes .clicks').count()==min(30,len(cfg['config']['routes']))
    page.locator('#sort-clicks').click();values=page.locator('#routes .clicks').all_text_contents();numbers=[int(x.replace('.','')) for x in values];assert numbers==sorted(numbers,reverse=True)
    page.locator('#click-from').fill('2026-01-01');page.locator('#click-to').fill('2026-01-01');page.locator('#apply-click-dates').click();expect(page.locator('#routes .clicks').first).to_have_text('0')
    page.locator('#click-range').select_option('today');page.wait_for_load_state('networkidle');assert page.request.get(cfg['url']+'/api/routes').json()==cfg['config']
    for width in [1280,390]:page.set_viewport_size({'width':width,'height':850});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors and not writes;browser.close()
print(json.dumps({'account':cfg['username'],'equal_preview20_23_cancel_preserves_original':tested,'menu_returns_to_list':True,'clicks_dates_sorting':True,'zero_before_collection':True,'US_Eastern_timezone':True,'mobile_no_overflow':True,'configuration_writes':0,'javascript_errors':0}))
