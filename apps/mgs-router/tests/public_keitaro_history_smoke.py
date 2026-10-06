"""Real HTTPS history/calendar QA. No route or click writes."""
import json,sys,os
from playwright.sync_api import sync_playwright,expect
os.environ['TMPDIR']='/root/.hermes/profiles/zeus/cache/scratch';cfg=json.load(sys.stdin);source=cfg['source'];config=cfg['config']
expected={}
for row in source['rows']:expected[row['route_key']]=expected.get(row['route_key'],0)+row['clicks']
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome');ctx=browser.new_context(viewport={'width':1280,'height':850});ctx.add_cookies(cfg['cookies']);page=ctx.new_page();errors=[];writes=[]
 page.on('pageerror',lambda e:errors.append(type(e).__name__));page.on('request',lambda r:writes.append(r.url) if r.method=='POST' else None)
 page.goto(cfg['url']+'/admin#rotas',wait_until='networkidle');expect(page.locator('#username')).to_have_text(cfg['username']);expect(page.locator('#click-period-notice')).to_contain_text('Histórico Keitaro importado');assert 'sem histórico anterior' not in page.locator('#click-period-notice').inner_text()
 for from_day,to_day in [(source['matched_dates'][0],source['matched_dates'][1]),('2026-01-22','2026-01-22'),('2026-09-01','2026-09-30')]:
  exp={}
  for row in source['rows']:
   if from_day<=row['day']<=to_day:exp[row['route_key']]=exp.get(row['route_key'],0)+row['clicks']
  response=page.request.get(cfg['url']+'/api/clicks',params={'from':from_day,'to':to_day});assert response.status==200;actual=response.json();assert actual['counts']==exp and actual['failed_writes']==0 and actual['history']['imported_clicks']==source['matched_clicks']
  page.locator('#click-from').fill(from_day);page.locator('#click-to').fill(to_day);page.locator('#apply-click-dates').click();page.wait_for_load_state('networkidle')
  for row in page.locator('#routes tr.route').all():
   url=row.locator('a.path').get_attribute('href');key=url.partition('://')[2].replace('/','\n/',1);expect(row.locator('.clicks')).to_have_text(format(exp.get(key,0),',').replace(',','.'))
 page.locator('#click-range').select_option('all');page.wait_for_load_state('networkidle');page.locator('#sort-clicks').click();nums=[int(x.replace('.','')) for x in page.locator('#routes .clicks').all_text_contents()];assert nums==sorted(nums,reverse=True)
 best=max(expected,key=expected.get);host,path=best.split('\n');page.locator('#search').fill(host+path);expect(page.locator('#routes tr.route')).to_have_count(1);row=page.locator('#routes tr.route');assert int(row.locator('.clicks').inner_text().replace('.',''))>=expected[best]
 row.locator('.text-link').first.click();page.locator('#nav-routes').click();expect(page.locator('#editor')).not_to_be_visible();assert page.request.get(cfg['url']+'/api/routes').json()==config
 for width in [1280,390]:page.set_viewport_size({'width':width,'height':850});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors and not writes;browser.close()
print(json.dumps({'account':cfg['username'],'historical_API_all444_campaign_totals_exact':True,'historical_calendar_all_firstday_September_exact':True,'history_notice_native_date_preserved':True,'all_period_sort_descending':True,'production_writes':0,'mobile_no_overflow':True,'javascript_errors':0}))
