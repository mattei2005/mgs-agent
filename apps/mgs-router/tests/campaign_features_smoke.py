import json,sys,os
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
    context=browser.new_context(viewport={'width':1280,'height':850})
    context.add_cookies([{'name':'mgs_session','value':cfg['session'],'url':cfg['url'],'httpOnly':True,'sameSite':'Strict'}])
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(type(e).__name__))
    page.goto(cfg['url']+'/admin#rotas');expect(page.locator('#routes tr.route')).to_have_count(3)
    for n in [20,23]:
        page.locator('#search').fill('Equal '+str(n));page.locator('#routes .text-link').first.click()
        expect(page.locator('.target-weight')).to_have_count(n);page.locator('#equal-weights').click()
        weights=[float(x) for x in page.locator('.target-weight').evaluate_all('(items)=>items.map(i=>i.value)')]
        assert len(set(weights))==1 and abs(weights[0]-100/n)<1e-10
        expect(page.locator('#weight-notice')).to_contain_text('igual')
        page.locator('#save').click();expect(page.locator('#editor')).not_to_be_visible()
        page.locator('#routes .text-link').first.click();expect(page.locator('.target-weight').first).to_have_value(str(weights[0]).rstrip('0').rstrip('.') if weights[0].is_integer() else str(weights[0]))
        page.locator('#nav-routes').click();expect(page.locator('#editor')).not_to_be_visible();expect(page.locator('#search')).to_have_value('Equal '+str(n))
    page.locator('#search').fill('Clicks');expect(page.locator('#routes .clicks')).to_have_text('0')
    resp=page.request.get(cfg['url']+'/click',headers={'Host':'go.example.com'},max_redirects=0);assert resp.status==302
    page.locator('#apply-click-dates').click();expect(page.locator('#routes .clicks')).to_have_text('1')
    page.locator('#sort-clicks').click();expect(page.locator('#routes .clicks')).to_have_text('1')
    page.locator('#click-from').fill('2026-01-01');page.locator('#click-to').fill('2026-01-01');page.locator('#apply-click-dates').click();expect(page.locator('#routes .clicks')).to_have_text('0')
    page.locator('#click-range').select_option('all');expect(page.locator('#routes .clicks')).to_have_text('1')
    page.locator('#click-from').fill('2026-10-07');page.locator('#click-to').fill('2026-10-06');page.locator('#apply-click-dates').click();expect(page.locator('#message')).to_contain_text('inicial')
    page.locator('#nav-destinations').click();page.locator('#new-destination').click();page.locator('#nav-destinations').click();expect(page.locator('#destination-editor')).not_to_be_visible()
    for width in [1280,390]:
        page.set_viewport_size({'width':width,'height':850});page.locator('#nav-routes').click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors;browser.close()
print(json.dumps({'equal20_23_saved_reload':True,'navigation_same_tab_list':True,'realGET_click_calendar_sort':True,'date_range_zero_all_invalid':True,'mobile_no_overflow':True,'javascript_errors':0}))
