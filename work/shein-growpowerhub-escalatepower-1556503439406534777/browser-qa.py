import json,sys,re,pathlib,time
from urllib.parse import urlencode,urlsplit,parse_qs
from playwright.sync_api import sync_playwright
W=pathlib.Path('/root/mgs-agent/work/shein-growpowerhub-escalatepower-1556503439406534777')
phase=sys.argv[1]
rows=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args=['--disable-dev-shm-usage'])
 context=browser.new_context(viewport={'width':390,'height':844},locale='en-US',timezone_id='America/New_York')
 page=context.new_page()
 for site in ['growpowerhub','escalatepower']:
  configs=json.load(open(W/(site+'-landings-inactive.json')))
  if phase=='canary':configs=[i for i in configs if i['manager_code']=='G001']
  for item in configs:
   slug=item['slug'];model=item['layout_template'];base=f'https://{site}.com/quiz/us/{slug}/'
   tracking={'utm_source':'facebook','utm_medium':item['manager_code'].lower()+'-s','utm_campaign':'mgs-qa-1556503439406534777','utm_adgroup':'qa-'+slug,'fbclid':'qa-fbclid','gclid':'qa-gclid','custom_qa':'preserved'}
   errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
   response=page.goto(base+'?'+urlencode(tracking),wait_until='load',timeout=45000)
   assert response.status==200,(base,response.status)
   page.wait_for_function('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)',timeout=20000)
   dom=page.evaluate('''() => ({lang:document.documentElement.lang, model:document.body.dataset.model, manager:document.body.dataset.manager,title:document.querySelector('h1').innerText,ctas:Array.from(document.querySelectorAll('[data-mgs-dq-cta]')).map(a=>a.href),images:Array.from(document.images).map(i=>({src:i.currentSrc,width:i.naturalWidth,height:i.naturalHeight})),labels:Array.from(document.querySelectorAll('.mgs-dq-category-name')).map(e=>e.innerText),forms:document.querySelectorAll('form,input').length,scripts:Array.from(document.scripts).filter(s=>s.src).map(s=>s.src),styles:Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(s=>s.href)})''')
   assert dom['lang']=='en-US' and dom['model']==model and dom['manager']==item['manager_code'],dom
   assert dom['title']==item['title'] and dom['forms']==0
   assert len(dom['ctas'])==(7 if model=='lp3' else 2)
   assert dom['images'][0]['src']==item['logo_url']
   assert dom['scripts'] and dom['styles'] and all(u.startswith('https://') for u in dom['scripts']+dom['styles'])
   assert not any('yolokfx.com' in json.dumps(v) for v in dom.values())
   for href in dom['ctas']:
    dest=urlsplit(href);q=parse_qs(dest.query)
    assert dest.netloc==site+'.com' and dest.path=='/rec-us-app-shein-circle-of-style/'
    assert all(q.get(k)==[v] for k,v in tracking.items()),q
   if model=='lp3':
    assert dom['labels']==[c['text'] for c in item['categories']]
    assert [i['src'] for i in dom['images'][1:]]==[c['image_url'] for c in item['categories']]
    page.wait_for_function('document.querySelector("[data-mgs-dq-countdown]").innerText!=="--:--:--"')
    countdown=page.locator('[data-mgs-dq-countdown]').inner_text();assert re.match(r'^\d{2}:\d{2}:\d{2}$',countdown),countdown
    toggle=page.locator('[data-mgs-dq-disclaimer-toggle]');assert toggle.get_attribute('aria-expanded')=='false'
    toggle.click();assert toggle.get_attribute('aria-expanded')=='true' and page.locator('[data-mgs-dq-disclaimer-box]').is_visible()
    toggle.click();assert toggle.get_attribute('aria-expanded')=='false'
   viewports=[]
   for width,height in [(320,700),(360,800),(390,844)]+([(1366,900)] if item['manager_code']=='G001' else []):
    page.set_viewport_size({'width':width,'height':height})
    geometry=page.evaluate('''() => {let e=document.querySelector('.mgs-dq-card,.mgs-dq-category-card');let r=e.getBoundingClientRect();return {inner:innerWidth,scroll:document.documentElement.scrollWidth,left:r.left,right:r.right,bg:getComputedStyle(e).backgroundColor}}''')
    assert geometry['scroll']<=geometry['inner'] and geometry['left']>=0 and geometry['right']<=geometry['inner'],geometry
    viewports.append({'width':width,'height':height,**geometry})
    if item['manager_code']=='G001' and width==390:page.screenshot(path=str(W/f'{phase}-{site}-{slug}-390.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844})
   landing_errors=list(errors)
   assert not landing_errors,landing_errors
   with page.expect_navigation(wait_until='domcontentloaded',timeout=45000) as nav:page.locator('[data-mgs-dq-cta]').first.click()
   rec=nav.value;assert rec.status==200,(base,rec.status)
   target=urlsplit(page.url);q=parse_qs(target.query)
   assert target.netloc==site+'.com' and target.path=='/rec-us-app-shein-circle-of-style/'
   assert all(q.get(k)==[v] for k,v in tracking.items()),q
   row={'site':site,'slug':slug,'status':response.status,'dom':dom,'viewports':viewports,'click_status':rec.status,'target':page.url,'landing_js_errors':landing_errors}
   rows.append(row);(W/(phase+'-browser-validation.json')).write_text(json.dumps(rows,indent=2))
   print(site,slug,'PASS',flush=True)
 browser.close()
expected=4 if phase=='canary' else 24
assert len(rows)==expected and len(set((r['site'],r['slug']) for r in rows))==expected
print(json.dumps({'phase':phase,'passed':len(rows),'expected':expected,'clicks':sum(r['click_status']==200 for r in rows)}))
