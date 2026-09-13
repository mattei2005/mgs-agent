import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const phase=process.argv[2]||'stage';
assert.ok(['stage','production'].includes(phase));
const root=new URL('../',import.meta.url).pathname.replace(/\/$/,'');
const candidate=JSON.parse(await fs.readFile(root+'/private/manager-roi-no-media-1548779265607073944/candidate.json','utf8'));
const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);const credentials=JSON.parse(Buffer.concat(chunks).toString());
const base='https://dash.mgsdigitalcorp.com',compact=value=>String(value).replace(/\s+/g,' ');let browser;
try{
 browser=await chromium.launch({headless:true,executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/New_York'});
 if(phase==='stage')await context.route('**/api/manager-workspace?*',route=>{const u=new URL(route.request().url());return u.searchParams.get('period')==='2026-09'&&['icaro',null].includes(u.searchParams.get('manager'))?route.fulfill({json:candidate}):route.continue();});
 const page=await context.newPage(),errors=[];let financialPosts=0;page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST'&&!r.url().includes('/api/auth/'))financialPosts++;});page.setDefaultTimeout(60000);
 await page.goto(base+'/login');await page.locator('#username').fill(credentials.username);await page.locator('#password').fill(credentials.password);await page.locator('button[type=submit]').click();await page.waitForSelector('.cards');
 await page.goto(base+'/operations?view=manager&manager=icaro&period=2026-09');await page.waitForSelector('.manager-block');
 const block=page.locator('.manager-block').filter({has:page.locator('summary',{hasText:'Portal Relevante'})}).first();await block.waitFor();if(!await block.evaluate(e=>e.open))await block.locator('summary').click();const select=block.locator('[data-manager-group]');if(await select.locator('option[value="US"]').count())await select.selectOption('US');
 const row=block.locator('tr[data-manager-day="2026-09-12"]');await row.waitFor();const cells=(await row.locator('td').allInnerTexts()).map(compact),roiGross=cells.at(-2),roiNet=cells.at(-1);assert.equal(roiGross,'—');assert.equal(roiNet,'—');
 const apiResponse=await context.request.get(base+'/api/manager-workspace?period=2026-09&manager=icaro');assert.equal(apiResponse.status(),200);const api=phase==='stage'?candidate:await apiResponse.json(),apiBlock=api.blocks.find(x=>x.label==='Portal Relevante'),apiRow=apiBlock.rows.find(x=>x.date==='2026-09-12'),grossIndex=apiBlock.columns.indexOf('ROI · GROSS · US'),netIndex=apiBlock.columns.indexOf('ROI · NET · US');assert.equal(apiRow.values[grossIndex],'');assert.equal(apiRow.values[netIndex],'');
 const views=[];for(const width of [1440,390]){await page.setViewportSize({width,height:1000});const scrollWidth=await page.evaluate(()=>document.documentElement.scrollWidth);assert.ok(scrollWidth<=width+1);views.push({width,scrollWidth});}
 assert.equal(financialPosts,0);assert.deepEqual(errors,[]);console.log(JSON.stringify({pass:true,phase,username:credentials.username,revision:api.revision,manager_row:cells,roi_gross:roiGross,roi_net:roiNet,api_roi_gross:apiRow.values[grossIndex],api_roi_net:apiRow.values[netIndex],viewports:views,financial_posts:financialPosts,js_errors:errors.length}));
}finally{if(browser)await browser.close();}
