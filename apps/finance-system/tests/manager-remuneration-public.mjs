import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const phase=process.argv[2]||'stage';
assert.ok(['stage','production'].includes(phase));
const root=new URL('../',import.meta.url).pathname.replace(/\/$/,'');
const evidence=root+'/private/manager-remuneration-card-1548770990954119179';
const candidate=JSON.parse(await fs.readFile(evidence+'/candidate.json','utf8'));
const chunks=[];
for await(const chunk of process.stdin)chunks.push(chunk);
const credentials=JSON.parse(Buffer.concat(chunks).toString());
const base='https://dash.mgsdigitalcorp.com',compact=value=>String(value).replace(/\s+/g,' ');
let browser;
try{
 browser=await chromium.launch({headless:true,executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/New_York'});
 if(phase==='stage'){
  await context.route('**/operations.js*',route=>route.fulfill({path:root+'/public/operations.js',contentType:'application/javascript'}));
  await context.route('**/operations.css*',route=>route.fulfill({path:root+'/public/operations.css',contentType:'text/css'}));
  await context.route('**/api/manager-workspace?*',route=>{const url=new URL(route.request().url());return url.searchParams.get('period')==='2026-09'&&url.searchParams.get('manager')==='icaro'?route.fulfill({json:candidate}):route.continue();});
 }
 const page=await context.newPage(),errors=[];let financialPosts=0;
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>{if(request.method()==='POST'&&!request.url().includes('/api/auth/'))financialPosts++;});
 page.setDefaultTimeout(60000);
 await page.goto(base+'/login');
 await page.locator('#username').fill(credentials.username);
 await page.locator('#password').fill(credentials.password);
 await page.locator('button[type=submit]').click();
 await page.waitForSelector('.cards');
 await page.goto(base+'/operations?view=manager&manager=icaro&period=2026-09');
 const remuneration=page.locator('[data-manager-remuneration]');
 await remuneration.waitFor();
 const remunerationText=compact(await remuneration.innerText());
 for(const expected of ['Remuneração atual','R$ 3.000,00','US$ 591,68','Piso mensal aplicado','Comissão calculada em 7%','R$ 68,59','Resultado atual','R$ 979,83','Meta para a comissão superar o piso','R$ 42.857,22','Faltam em resultado','R$ 41.877,39'])assert.ok(remunerationText.includes(expected),expected+' absent from '+remunerationText);
 assert.equal(await page.locator('[data-manager-current] .card').count(),2);
 assert.equal(await page.locator('[data-manager-estimates] .card').count(),3);
 assert.equal(await page.locator('[data-manager-current]').getByText('Comissão atual · 7%',{exact:true}).count(),0);
 const apiResponse=await context.request.get(base+'/api/manager-workspace?period=2026-09&manager=icaro');
 assert.equal(apiResponse.status(),200);
 const api=phase==='stage'?candidate:await apiResponse.json();
 assert.equal(api.card_summary.remuneration.status,'floor');
 assert.equal(api.card_summary.remuneration.due.brl,'3000');
 assert.equal(api.card_summary.remuneration.floor_switch_result_brl,'42857.22');
 const viewports=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  const scrollWidth=await page.evaluate(()=>document.documentElement.scrollWidth);
  assert.ok(scrollWidth<=width+1,'manager overflow '+width+' -> '+scrollWidth);
  viewports.push({width,scrollWidth});
 }
 await page.goto(base+'/operations?view=payments&period=2026-09');
 await page.locator('#party').waitFor();
 await page.locator('#party').selectOption('personnel|154');
 await page.waitForFunction(()=>document.querySelector('#party')?.value==='personnel|154'&&document.querySelector('#content')?.textContent.includes('6.000,00'));
 const paymentsText=compact(await page.locator('#content').innerText());
 for(const expected of ['Saldo anterior R$ 3.000,00','Remuneração do mês R$ 3.000,00','Ajustes − pagamentos R$ 0,00','Saldo a pagar R$ 6.000,00'])assert.ok(paymentsText.includes(expected),expected+' absent from payments');
 assert.ok(!paymentsText.includes('Comissão calculada'));
 const ledgerResponse=await context.request.get(base+'/api/finance/ledger?period=2026-09&counterparty=personnel%7C154');
 assert.equal(ledgerResponse.status(),200);
 const ledger=await ledgerResponse.json();
 assert.equal(ledger.due,300000);assert.equal(ledger.previous,300000);assert.equal(ledger.balance,600000);
 assert.equal(financialPosts,0);assert.deepEqual(errors,[]);
 const out={pass:true,phase,revision:api.revision,remuneration_text:remunerationText,payments_text:paymentsText,api_remuneration:api.card_summary.remuneration,ledger:{previous:ledger.previous,due:ledger.due,balance:ledger.balance,entries:ledger.entries.length},viewports,financial_posts:financialPosts,js_errors:errors.length};
 console.log(JSON.stringify(out));
}finally{if(browser)await browser.close();}
