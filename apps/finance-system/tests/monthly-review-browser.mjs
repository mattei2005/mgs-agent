import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const root=new URL('../',import.meta.url).pathname,w=root+'private/prevention-release-1551755722700624003/',phase=process.argv[2];assert.ok(['stage','production'].includes(phase));
let raw='';for await(const c of process.stdin)raw+=c;const cookies=JSON.parse(raw),origin='https://dash.mgsdigitalcorp.com',errors=[],writes=[],requests=[];
const captured=phase==='stage'?JSON.parse(await fs.readFile(w+'stage-responses.json','utf8')):null;
const browser=await chromium.launch({executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',headless:true,args:['--no-sandbox']});
try{
 const context=await browser.newContext({locale:'pt-BR',viewport:{width:1440,height:1000}});await context.addCookies(cookies);
 await context.route('**/api/**',async route=>{
  const req=route.request(),u=new URL(req.url());if(req.method()!=='GET'){writes.push(u.pathname);return route.abort();}
  requests.push(u.pathname);
  if(captured&&u.pathname==='/api/monthly-review')return route.fulfill({json:captured.responses[u.pathname+'?period='+u.searchParams.get('period')]});
  if(captured&&u.pathname==='/api/monthly-trace'){
   const period=u.searchParams.get('period'),revision=captured.responses['/api/monthly-review?period='+period].revision;
   if(String(revision)!==u.searchParams.get('revision'))return route.fulfill({status:409,json:{error:'Revisão mudou; atualize.'}});
   let rows=period==='2026-08'?captured.augTrace:period==='2026-09'?captured.sepTrace:[],q=(u.searchParams.get('q')||'').toLocaleLowerCase('pt-BR');
   if(q)rows=rows.filter(r=>[r.site,r.manager,r.source_manager_tag,r.date,r.country,r.source_type,...r.adjustments.map(a=>a.authority)].join(' ').toLocaleLowerCase('pt-BR').includes(q));const offset=Number(u.searchParams.get('offset')||0);return route.fulfill({json:{period,revision,offset,count:rows.length,limit:100,has_more:offset+100<rows.length,rows:rows.slice(offset,offset+100)}});
  }
  return route.continue();
 });
 if(captured)for(const f of ['review.html','review.js','review.css','navigation.js'])await context.route('**/'+f+'*',r=>r.fulfill({path:root+'public/'+f,contentType:f.endsWith('.js')?'application/javascript':f.endsWith('.css')?'text/css':'text/html'}));
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 const response=await context.request.get(origin+'/api/periods');assert.equal(response.status(),200);const periods=(await response.json()).filter(p=>p.id>='2026-08');assert.equal(periods.length,17);
 const checked=[];
 for(const p of periods){await page.goto(origin+'/review.html?period='+p.id);await page.waitForFunction(()=>document.querySelector('#content')?.getAttribute('aria-busy')==='false'&&document.querySelector('#traceCount')?.textContent);assert.equal(await page.locator('#period').inputValue(),p.id);assert.ok((await page.locator('#content').innerText()).includes('consulta somente leitura'));assert.ok((await page.locator('#subtitle').innerText()).includes('revisão'));checked.push(p.id);}
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto(origin+'/review.html?period=2026-08');await page.waitForSelector('#traceSearch');await page.waitForFunction(()=>document.querySelector('#traceCount')?.textContent);
  await page.locator('#traceSearch').fill('1551714950781866035');await page.locator('#traceApply').click();await page.waitForFunction(()=>document.querySelector('#traceCount')?.textContent==='Exibindo 1–8 de 8');
  await page.locator('.trace-detail summary').first().click();assert.ok((await page.locator('.trace-detail[open]').innerText()).includes('Correções de atribuição'));
  assert.ok(await page.locator('a[href*="1551714950781866035"]').count()>0);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'mobile horizontal overflow');
  await page.screenshot({path:w+'review-'+phase+'-'+width+'.png',fullPage:false});
 }
 await page.setViewportSize({width:1440,height:1000});await page.goto(origin+'/?period=2026-09');await page.waitForSelector('[data-financial-total],.cards');assert.equal(await page.locator('a[href*="review.html"]').count(),1);await page.locator('a[href*="review.html"]').click();await page.waitForSelector('#traceSearch');assert.equal(await page.locator('#period').inputValue(),'2026-09');
 for(const manager of ['icaro','joe','isliago','kelly','nicolas']){const r=await context.request.get(origin+'/api/manager-workspace?period=2026-09&manager='+manager);assert.equal(r.status(),200);}
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
 const result={pass:true,phase,periods:checked,desktop_mobile:[1440,390],openzed_bidirectional_records:8,read_only:true,financial_posts:writes,js_errors:errors,source:captured?'real isolated PostgreSQL snapshots + authenticated production reads':'live authenticated production',api_requests:requests.length};await fs.writeFile(w+'browser-'+phase+'.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{await browser.close();}
