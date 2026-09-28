import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const root=new URL('../',import.meta.url).pathname,w=root+'private/vigency-release-1551783001678024736/',phase=process.argv[2];assert.ok(['stage','production'].includes(phase));
let raw='';for await(const c of process.stdin)raw+=c;const cookies=JSON.parse(raw),origin='https://dash.mgsdigitalcorp.com',errors=[],writes=[];
const captured=phase==='stage'?JSON.parse(await fs.readFile(w+'stage-responses.json','utf8')):null;
const browser=await chromium.launch({executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',headless:true,args:['--no-sandbox']});
try{
 const context=await browser.newContext({locale:'pt-BR',viewport:{width:1440,height:1000}});await context.addCookies(cookies);
 await context.route('**/api/**',async route=>{
  const req=route.request(),u=new URL(req.url());if(req.method()!=='GET'){writes.push(u.pathname);return route.abort();}
  if(captured&&['/api/monthly-review','/api/period-preview'].includes(u.pathname))return route.fulfill({json:captured.responses[u.pathname+'?period='+u.searchParams.get('period')]});
  if(captured&&u.pathname==='/api/monthly-trace')return route.fulfill({json:{count:0,offset:0,limit:100,has_more:false,rows:[]}});
  return route.continue();
 });
 if(captured)for(const f of ['review.html','review.js','review.css','navigation.js','period-preview.js'])await context.route('**/'+f+'*',r=>r.fulfill({path:root+'public/'+f,contentType:f.endsWith('.js')?'application/javascript':f.endsWith('.css')?'text/css':'text/html'}));
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 const response=await context.request.get(origin+'/api/periods');assert.equal(response.status(),200);const periods=(await response.json()).filter(p=>p.id>='2026-08');assert.equal(periods.length,17);const checked=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  for(const p of periods){await page.goto(origin+'/review.html?period='+p.id);await page.waitForFunction(id=>document.querySelector('#periodPreview')?.dataset.loaded===id,p.id);assert.equal(await page.locator('#period').inputValue(),p.id);const text=await page.locator('#periodPreview').innerText();assert.ok(text.includes('nenhuma regra ou valor é aplicado'));assert.equal(await page.locator('#periodPreview button').count(),0);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'mobile horizontal overflow');checked.push({period:p.id,width});}
  await page.goto(origin+'/review.html?period=2026-09');await page.waitForFunction(()=>document.querySelector('#periodPreview')?.dataset.loaded==='2026-09');assert.ok((await page.locator('#periodPreview').innerText()).includes('Continuidade em outubro exige confirmação'));await page.locator('#periodPreview summary').filter({hasText:'Cadastros já existentes'}).click();assert.ok((await page.locator('#periodPreview').innerText()).includes('Comparar registros'));await page.locator('#periodPreview summary').filter({hasText:'Comparar registros'}).first().click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await page.screenshot({path:w+'preview-'+phase+'-'+width+'.png',fullPage:false});
 }
 await page.selectOption('#period','2026-08');await page.waitForFunction(()=>document.querySelector('#periodPreview')?.dataset.loaded==='2026-08');await page.selectOption('#period','2027-12');await page.waitForFunction(()=>document.querySelector('#periodPreview')?.dataset.loaded==='2027-12');assert.ok((await page.locator('#periodPreview').innerText()).includes('Fim do horizonte cadastrado'));
 for(const manager of ['icaro','joe','isliago','kelly','nicolas'])assert.equal((await context.request.get(origin+'/api/manager-workspace?period=2026-09&manager='+manager)).status(),200);
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);assert.equal(checked.length,34);
 const result={pass:true,phase,periods:periods.map(p=>p.id),checked,desktop_mobile:[1440,390],read_only:true,financial_posts:writes,js_errors:errors,source:captured?'real isolated PostgreSQL snapshots with local candidate UI':'live authenticated production'};await fs.writeFile(w+'browser-'+phase+'.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{await browser.close();}
