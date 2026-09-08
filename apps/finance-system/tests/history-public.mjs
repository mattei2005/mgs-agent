import {chromium} from '@playwright/test';import fs from 'node:fs/promises';import assert from 'node:assert/strict';
const D='private/history-import-1546884731436671056',base='https://dash.mgsdigitalcorp.com',chunks=[];for await(const c of process.stdin)chunks.push(c);const credentials=JSON.parse(Buffer.concat(chunks).toString());const build=JSON.parse(await fs.readFile(D+'/built.json','utf8'));
const browser=await chromium.launch({executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',headless:true,args:['--no-sandbox']});const proof={pass:false,real_logins:0,history_month_checks:0,viewports:0,denials:0,public_cells_verified:0,js_errors:0,users:[]};
try{
 for(const key of ['rodolfo','nicolas','joe','isliago','kelly','icaro']){
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();page.on('pageerror',()=>proof.js_errors++);await page.goto(base+'/login');await page.locator('input[name="username"]').fill(key);await page.locator('input[name="password"]').fill(credentials[key]);await Promise.all([page.waitForURL(u=>!u.pathname.startsWith('/login')),page.locator('button[type="submit"]').click()]);const me=await(await context.request.get(base+'/api/auth/me')).json();assert.equal(me.role,key==='rodolfo'?'owner':'manager');proof.real_logins++;
  const get=async url=>{const r=await context.request.get(base+url);assert.equal(r.status(),200,url);return r.json();};
  if(key==='rodolfo'){
   for(const item of build.manifest){const requested=item.book==='george'?'icaro':item.book;const d=await get('/api/history?period='+item.period+'&book='+requested),expected=JSON.parse(await fs.readFile(D+'/payloads/'+item.file,'utf8'));assert.deepEqual(d.cells,expected.cells);proof.public_cells_verified+=d.cells.length;if(item.book==='principal'){assert.deepEqual(d.closure,expected.closure);assert.deepEqual(d.caixa,expected.caixa);}}
   const aug=await get('/api/finance/ledger?period=2026-08'),sep=await get('/api/finance/ledger?period=2026-09');assert.equal(aug.opening,71);assert.equal(aug.opening_source.period,'2026-07');assert.equal(aug.opening_source.source,'dash-frozen-snapshot');assert.equal(sep.previous,aug.balance);proof.july_to_august=true;
   await page.goto(base+'/');await page.locator('.cards').first().waitFor();await page.locator('#period').selectOption('2026-07');await page.waitForURL('**/history?period=2026-07');
  }else{
   const other=key==='joe'?'kelly':'joe';for(const book of ['principal',other,'george','caixa']){assert.equal((await context.request.get(base+'/api/history?period=2026-07&book='+book)).status(),403);proof.denials++;}
   for(const url of ['/api/workspace','/api/cells','/api/finance/users']){assert.equal((await context.request.get(base+url)).status(),403);proof.denials++;}
   await page.goto(base+'/operations?view=manager');await page.locator('.manager-block').first().waitFor();assert.equal(await page.locator('#period').inputValue(),'2026-08');await page.locator('#period').selectOption('2026-07');await page.waitForURL('**/history?period=2026-07&book='+key);
  }
  for(const period of [...new Set(build.manifest.map(m=>m.period))]){
   await page.goto(base+'/history?period='+period+'&book='+(key==='rodolfo'?'principal':key));await page.waitForFunction(()=>document.querySelector('#content')?.textContent.includes('Histórico fechado, somente leitura.')&&document.querySelector('#message').textContent==='');assert.equal(await page.locator('#period').inputValue(),period);assert.equal(await page.locator('#content button').count(),key==='icaro'&&period<'2026-03'?0:1);
   if(key!=='rodolfo'){assert.equal(await page.locator('#book option').count(),1);assert.equal(await page.locator('#book').inputValue(),key);assert.ok(!(await page.locator('#content').innerText()).includes('Fechamento e extrato · Geizian'));}
   if(key==='rodolfo'&&period==='2026-04')assert.ok((await page.locator('.history-warning').innerText()).includes('Diferença entre meses'));
   if(key==='icaro'&&period<'2026-03')assert.ok((await page.locator('#content').innerText()).includes('salário'));
   for(const width of [390,1440]){await page.setViewportSize({width,height:1000});await page.waitForTimeout(50);const overflow=await page.evaluate(()=>({width:innerWidth,doc:document.documentElement.scrollWidth,body:document.body.scrollWidth}));assert.ok(overflow.doc<=width+1,key+' '+period+' '+JSON.stringify(overflow));proof.viewports++;}
   const columns=page.locator('#columns');if(await columns.count()){const last=await columns.locator('option').last().getAttribute('value');await columns.selectOption(last);const rows=page.locator('#rows'),lastrow=await rows.locator('option').last().getAttribute('value');await rows.selectOption(lastrow);assert.ok((await page.locator('#rangeStatus').innerText()).includes('células preservadas'));}
   proof.history_month_checks++;
  }
  for(const month of ['2026-08','2026-09']){if(key==='rodolfo'){const d=await get('/api/workspace?period='+month);assert.equal(d.period.id,month);}else{const d=await get('/api/manager-workspace?period='+month);assert.equal(d.manager,key);assert.ok(d.blocks.length);}}
  assert.equal((await context.request.post(base+'/api/auth/logout',{headers:{Origin:base,'X-CSRF-Token':me.csrf},data:{}})).status(),200);assert.equal((await context.request.get(base+'/api/history')).status(),401);proof.denials++;proof.users.push({key,pass:true});await fs.writeFile(D+'/public-progress.json',JSON.stringify(proof));await context.close();
 }
 assert.equal(proof.real_logins,6);assert.equal(proof.history_month_checks,42);assert.equal(proof.viewports,84);assert.equal(proof.public_cells_verified,build.cells);assert.equal(proof.js_errors,0);proof.pass=true;await fs.writeFile(D+'/public-readback.json',JSON.stringify(proof,null,2));console.log(JSON.stringify(proof));
}finally{await browser.close();}
