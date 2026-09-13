import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';

const phase=process.argv[2]||'stage';
assert.ok(['stage','production'].includes(phase));
const root=new URL('../',import.meta.url).pathname.replace(/\/$/,'');
const base='https://dash.mgsdigitalcorp.com';
const chunks=[];
for await(const chunk of process.stdin)chunks.push(chunk);
const credentials=JSON.parse(Buffer.concat(chunks).toString());
const compact=value=>String(value).replace(/\s+/g,' ');
let browser;
try{
 browser=await chromium.launch({headless:true,executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/New_York'});
 if(phase==='stage'){
  for(const file of ['app.js','operations.js','media-spend.js'])await context.route(base+'/'+file+'*',route=>route.fulfill({path:root+'/public/'+file,contentType:'application/javascript'}));
 }
 const page=await context.newPage(),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.setDefaultTimeout(60000);
 await page.goto(base+'/login');
 await page.locator('#username').fill(credentials.username);
 await page.locator('#password').fill(credentials.password);
 await page.locator('button[type=submit]').click();
 await page.waitForSelector('.cards');
 const workspaceResponse=await context.request.get(base+'/api/workspace?period=2026-09');
 assert.equal(workspaceResponse.status(),200);
 const workspace=await workspaceResponse.json();
 const historyAssetResponse=await context.request.get(base+'/history-operations.js?v=1548729278156378185');
 assert.equal(historyAssetResponse.status(),200);
 const historyAsset=await historyAssetResponse.body(),historyAssetHash=createHash('sha256').update(historyAsset).digest('hex'),expectedHistoryHash=createHash('sha256').update(await fs.readFile(root+'/public/history-operations.js')).digest('hex');
 assert.equal(historyAssetHash,expectedHistoryHash);
 const factId='gam-email-2026-09-12-8d3f8c263b77|portal-relevante|US|g001-d|CAD';
 const fact=workspace.domain.facts.find(item=>item.id===factId);
 assert.ok(fact);
 assert.ok(Number(fact.gross)>0&&Number(fact.gross)<.01);
 await page.goto(base+'/?view=movement&period=2026-09');
 await page.waitForSelector('[data-site-list]');
 await page.locator('button[data-site="Portal Relevante"]').first().click();
 const edit=page.locator('button[data-edit-fact="'+factId.replaceAll('"','\\"')+'"]');
 await edit.waitFor({state:'attached'});
 const countryDetails=edit.locator('xpath=ancestor::details[1]');
 await countryDetails.evaluate(element=>{element.open=true;});
 await edit.waitFor();
 const ownerRow=edit.locator('xpath=ancestor::tr');
 const ownerText=compact(await ownerRow.innerText());
 assert.match(ownerText,/12\/09/);
 assert.match(ownerText,/< CA\$ 0,01/);
 assert.match(ownerText,/< US\$ 0,01/);
 assert.match(ownerText,/-< US\$ 0,01/);
 assert.match(ownerText,/US\$ 0,00/);
 const managerResponse=await context.request.get(base+'/api/manager-workspace?period=2026-09&manager=icaro');
 assert.equal(managerResponse.status(),200);
 const manager=await managerResponse.json();
 const block=manager.blocks.find(item=>item.label==='Portal Relevante');
 assert.ok(block);
 const apiRow=block.rows.find(item=>item.date==='2026-09-12');
 assert.ok(apiRow);
 await page.goto(base+'/operations?view=manager&manager=icaro&period=2026-09');
 await page.waitForSelector('.manager-block');
 const managerBlock=page.locator('.manager-block').filter({has:page.locator('summary',{hasText:'Portal Relevante'})}).first();
 await managerBlock.waitFor();
 if(!await managerBlock.evaluate(element=>element.open))await managerBlock.locator('summary').click();
 const managerRows=managerBlock.locator('tr[data-manager-day="2026-09-12"]');
 assert.ok(await managerRows.count()>0);
 const managerText=compact((await managerRows.allInnerTexts()).join(' | '));
 assert.match(managerText,/< 0,01/);
 assert.match(managerText,/-< 0,01/);
 const viewports=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  const scrollWidth=await page.evaluate(()=>document.documentElement.scrollWidth);
  assert.ok(scrollWidth<=width+1,'manager overflow '+width+' -> '+scrollWidth);
  viewports.push({view:'manager',width,scrollWidth});
 }
 await page.goto(base+'/?view=movement&period=2026-09');
 await page.waitForSelector('[data-site-list]');
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  const scrollWidth=await page.evaluate(()=>document.documentElement.scrollWidth);
  assert.ok(scrollWidth<=width+1,'owner overflow '+width+' -> '+scrollWidth);
  viewports.push({view:'owner',width,scrollWidth});
 }
 await page.goto(base+'/operations?view=manager&manager=icaro&period=2026-07');
 await page.waitForSelector('.manager-intro');
 assert.match(await page.locator('.manager-intro').innerText(),/Mês fechado/);
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({pass:true,phase,revision:workspace.revision,fact:{gross:fact.gross,net:fact.net,tax:fact.tax,profit:fact.profit},owner_row:ownerText,manager_rows:managerText,manager_api_row:apiRow,history_asset_sha256:historyAssetHash,closed_manager_loaded:true,viewports,js_errors:errors.length}));
}finally{if(browser)await browser.close();}
