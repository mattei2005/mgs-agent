import json,sys,os
from playwright.sync_api import sync_playwright
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch'
cfg=json.load(sys.stdin)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome')
    page=browser.new_page();origins=[]
    page.on('request',lambda r:origins.append(r.headers.get('origin','(absent)')) if r.method=='POST' and '/login' in r.url else None)
    page.goto(cfg['url']+'/login')
    # Deliberately empty native form: tests browser Origin, not credentials.
    with page.expect_response(lambda r:r.request.method=='POST' and '/login' in r.url) as event:
        page.locator('form').evaluate('(form)=>form.submit()')
    response=event.value
    result={'native_form_origin':origins[-1],'post_status':response.status,'location':response.headers.get('location')}
    browser.close()
print(json.dumps(result))
