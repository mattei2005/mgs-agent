import json,sys,os
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
 ctx=browser.new_context(viewport={'width':1280,'height':850})
 ctx.add_cookies([{'name':'mgs_session','value':cfg['session'],'url':cfg['url'],'httpOnly':True,'sameSite':'Strict'}])
 page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(type(e).__name__))
 page.goto(cfg['url']+'/admin',wait_until='networkidle')
 expect(page.locator('#routes .route')).to_have_count(3)
 page.locator('#search').fill('/relative')
 page.get_by_role('button',name='Editar destino',exact=True).click()
 expect(page.locator('#weight-notice')).to_contain_text('sem arredondamento')
 expect(page.locator('#query-notice')).to_contain_text('Modo Keitaro')
 expect(page.locator('.target-weight')).to_have_count(3)
 assert page.locator('.target-weight').evaluate_all('(els)=>els.map(e=>e.value)')==['14','14','14']
 with page.expect_response(lambda r:r.url.endswith('/api/routes') and r.request.method=='POST') as response:page.locator('#save').click()
 assert response.value.status==200
 saved=page.request.get(cfg['url']+'/api/routes').json()
 relative=next(r for r in saved['routes'] if r['path']=='/relative')
 assert relative['relative_weights'] and relative['keitaro_query'] and [t['weight'] for t in relative['destinations']]==[14,14,14]
 page.reload(wait_until='networkidle');page.locator('#search').fill('/empty')
 expect(page.locator('#routes summary')).to_have_text('Sem destino — HTTP 500 (Keitaro)')
 page.get_by_role('button',name='Editar destino',exact=True).click()
 assert not page.locator('#destination').evaluate('(e)=>e.required')
 with page.expect_response(lambda r:r.url.endswith('/api/routes') and r.request.method=='POST') as response:page.locator('#save').click()
 assert response.value.status==200
 saved=page.request.get(cfg['url']+'/api/routes').json();empty=next(r for r in saved['routes'] if r['path']=='/empty')
 assert empty['response_status']==500 and empty['keitaro_query'] and not empty.get('destination')
 page.locator('#search').fill('/fragment');page.get_by_role('button',name='Editar destino',exact=True).click()
 assert '#PAGE_ID#' in page.locator('#destination').input_value()
 with page.expect_response(lambda r:r.url.endswith('/api/routes') and r.request.method=='POST') as response:page.locator('#save').click()
 assert response.value.status==200
 assert not errors
 browser.close()
print(json.dumps({'synthetic_UI_roundtrips':3,'relative_weights_and_query_and_empty_and_fragment_preserved':True,'js_errors':0}))
