import {chromium} from '/root/mgs-agent/apps/finance-system/node_modules/@playwright/test/index.mjs';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const chunks=[];for await(const c of process.stdin)chunks.push(c);const credential=JSON.parse(Buffer.concat(chunks).toString());let browser;
try{
 browser=await chromium.launch({headless:true,executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/New_York'}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(60000);
 await page.goto('https://dash.mgsdigitalcorp.com/');await page.waitForURL('**/login');await page.locator('#username').fill(credential.username);await page.locator('#password').fill(credential.password);await page.locator('button[type=submit]').click();await page.waitForSelector('.cards');
 const me=await context.request.get('https://dash.mgsdigitalcorp.com/api/auth/me');assert.equal(me.status(),200);const ident=await me.json();assert.equal(ident.username,'rodolfo');assert.equal(ident.role,'owner');
 const res=await context.request.get('https://dash.mgsdigitalcorp.com/api/workspace?period=2026-09');assert.equal(res.status(),200);const w=await res.json();assert.equal(w.id,'workspace-2026-09');assert.equal(w.state,'draft');assert.equal(w.period.id,'2026-09');
 await fs.writeFile('/root/mgs-agent/work/finance-revenue-1547692440574627921/workspace-before.json',JSON.stringify(w,null,2));
 const facts=w.domain.facts.filter(f=>f.date<='2026-09-09'),grossInputs=Object.values(w.model.inputs).filter(x=>x.metric==='gross'&&w.model.facts[x.fact_id]);
 const summary={status:'PASS',identity:ident.username,role:ident.role,id:w.id,revision:w.revision,state:w.state,sites:w.sites.length,facts_1_9:facts.length,gross_inputs:grossInputs.length,nonempty_gross_inputs:grossInputs.filter(x=>String(x.value??'')!=='').length,errors:errors.length};
 await page.getByRole('button',{name:/Sair/}).click();await page.waitForURL('**/login');
 console.log(JSON.stringify(summary));
}catch(e){console.log(JSON.stringify({status:'FAIL',name:e.name,message:String(e.message).slice(0,900)}));process.exitCode=1;}finally{await browser?.close();}
