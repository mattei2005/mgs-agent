import {chromium} from '@playwright/test';import assert from 'node:assert/strict';import fs from 'node:fs/promises';import path from 'node:path';import {openDatabase,root} from '../storage.mjs';import {createApp} from '../server.mjs';
const published=process.env.FINANCE_PUBLIC==='1',dir=path.join(root,'private/payroll-1546380179654451281');let browser,db,server;
try{
 let base='https://dash.mgsdigitalcorp.com',credential;
 if(published){const chunks=[];for await(const c of process.stdin)chunks.push(c);credential=JSON.parse(Buffer.concat(chunks).toString());}
 else{const e=JSON.parse(await fs.readFile(path.join(dir,'local-integration.json')));db=await openDatabase(e.directory);server=(await createApp(db)).listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));base='http://127.0.0.1:'+server.address().port;}
 browser=await chromium.launch({headless:true,executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args:['--no-sandbox']});const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);if(published){await page.waitForURL('**/login');await page.locator('#username').fill(credential.username);await page.locator('#password').fill(credential.password);await page.locator('button[type=submit]').click();}await page.waitForSelector('.cards');
 const get=async p=>{const res=await context.request.get(base+p);assert.equal(res.status(),200);return res.json();};
 await page.locator('#nav [data-view=admin]').click();await page.locator('#adminNav [data-view=personnel]').click();
 assert.ok((await page.locator('#content').innerText()).includes('Atividade'));assert.ok((await page.locator('#content').innerText()).includes('100.000, inclusive'));
 const periods=await get('/api/periods'),checks=[];
 for(const p of periods){const w=await get('/api/workspace?period='+p.id);const rows=w.domain.expenses.filter(e=>e.category==='personnel'&&e.label);assert.equal(rows.length,12);assert.ok(rows.every(e=>e.payroll_rule==='monthly-v1'));checks.push({period:p.id,rows:rows.length,pass:true});}
 for(const width of [390,768,1440]){
  await page.setViewportSize({width,height:900});
  for(const period of ['2026-08','2026-09','2027-12']){
   await page.locator('#period').selectOption(period);await page.waitForFunction(p=>document.querySelector('#period').value===p&&!document.querySelector('#period').disabled,period);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));assert.equal(await page.locator('#content tbody tr').count(),12);
   await page.locator('[data-expense="personnel|150"]').click();assert.equal(await page.locator('#employeeActivity').inputValue(),'INATIVO');assert.ok(await page.locator('#expenseStatus').count());await page.locator('#editor [data-close]').first().click();
  }
 }
 if(!published){
  await page.locator('[data-expense="personnel|155"]').click();assert.equal(await page.locator('#expenseAmount').inputValue(),'2000');assert.equal(await page.locator('#expenseCurrency').inputValue(),'BRL');await page.locator('#employeeActivity').selectOption('INATIVO');await page.locator('#save').click();await page.waitForFunction(()=>!document.querySelector('#editor').open,{timeout:90000});let w=await get('/api/workspace?period=2027-12');assert.equal(Number(w.domain.expenses.find(e=>e.id==='personnel|155').brl),0);
  await page.locator('[data-expense="personnel|155"]').click();assert.equal(await page.locator('#expenseAmount').inputValue(),'2000');await page.locator('#employeeActivity').selectOption('ATIVO');await page.locator('#save').click();await page.waitForFunction(()=>!document.querySelector('#editor').open,{timeout:90000});w=await get('/api/workspace?period=2027-12');assert.equal(Number(w.domain.expenses.find(e=>e.id==='personnel|155').brl),-2000);
 }
 assert.equal(errors.length,0,errors.join(';'));const out={pass:true,published,periods:checks,viewports:[390,768,1440],activity_and_review_separate:true,local_crud:!published,js_errors:0,production_financial_test_writes:0};await fs.writeFile(path.join(dir,published?'public-browser.json':'local-browser.json'),JSON.stringify(out,null,2));console.log(JSON.stringify({pass:true,published,periods:checks.length,js_errors:0}));
}catch(e){console.log(JSON.stringify({pass:false,published,error:e.message.slice(0,1000)}));process.exitCode=1;}finally{await browser?.close();if(server)await new Promise(r=>server.close(r));await db?.close();}
