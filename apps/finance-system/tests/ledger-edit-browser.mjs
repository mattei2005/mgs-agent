import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {ledgerVersion} from '../ledger-edit.mjs';
const root=new URL('../',import.meta.url).pathname,phase=process.argv[2];assert.ok(['stage','production'].includes(phase));
let raw='';for await(const c of process.stdin)raw+=c;const cookies=JSON.parse(raw);const origin='https://dash.mgsdigitalcorp.com',errors=[],writes=[];
const browser=await chromium.launch({executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',headless:true,args:['--no-sandbox']});
try{
 const context=await browser.newContext({locale:'pt-BR',viewport:{width:1440,height:1000}});await context.addCookies(cookies);
 await context.route('**/api/**',async route=>{if(route.request().method()!=='GET'){writes.push(route.request().url());return route.abort();}if(phase==='stage'&&route.request().url().includes('/api/finance/ledger?')){const response=await route.fetch(),data=await response.json();data.entries=data.entries.map(e=>({...e,version:ledgerVersion(e)}));return route.fulfill({response,json:data});}return route.continue();});
 if(phase==='stage')for(const f of ['operations.js','operations.css'])await context.route('**/'+f+'*',r=>r.fulfill({path:root+'public/'+f,contentType:f.endsWith('.js')?'application/javascript':'text/css'}));
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 const get=async path=>{const r=await context.request.get(origin+path);assert.equal(r.status(),200,path);return r.json();};
 const available=await get('/api/periods'),periods=available.map(p=>p.id).filter(p=>p>='2026-08');assert.equal(periods.length,17);
 let august;
 for(const period of periods){
  const ledger=await get('/api/finance/ledger?period='+period+'&counterparty=geizian');if(period==='2026-08')august=ledger;
  await page.goto(origin+'/operations?view=payments&period='+period);await page.waitForSelector('#adjustment');await page.waitForFunction(()=>document.querySelector('#content').textContent.includes('Itens excluídos'));
  assert.equal(await page.locator('#period').inputValue(),period);assert.equal(await page.locator('.ledger-actions > button[data-ledger-edit]').count(),ledger.entries.filter(e=>!e.voided_at).length);
  const text=await page.locator('#content').innerText();assert.ok(!/ESTORNADO|Estornar/.test(text));assert.ok(text.includes('Histórico de Atividades'));
 }
 const active=august.entries.filter(e=>!e.voided_at);assert.equal(active.length,5);assert.equal(active.reduce((s,e)=>s+Number(e.amount_cents)*Number(e.direction),0),89960);assert.equal(august.entries.filter(e=>e.voided_at).length,6);
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto(origin+'/operations?view=payments&period=2026-08');await page.waitForSelector('.ledger-actions');
  await page.locator('.ledger-actions > button[data-ledger-edit]').first().click();await page.waitForSelector('#dialog[open]');assert.ok((await page.locator('#dialogTitle').textContent()).includes('Editar'));assert.ok(await page.locator('[name=description]').inputValue());assert.ok(Number(await page.locator('[name=amount]').inputValue())>0);assert.equal(await page.locator('[name=nature] option').count(),3);await page.locator('#cancel').click();
  await page.locator('.ledger-actions summary').first().click();await page.locator('[data-ledger-delete]').first().click();await page.waitForSelector('#dialog[open]');assert.ok((await page.locator('#dialogTitle').textContent()).includes('Excluir'));assert.ok((await page.locator('#fields').textContent()).includes('histórico'));await page.locator('#cancel').click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
 }
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);const out={pass:true,phase,periods,active_august:active.length,active_cents:89960,removed_hidden:6,edit_delete_modals:true,desktop_mobile:[1440,390],js_errors:errors,financial_posts:writes};await fs.writeFile(root+'private/payments-edit-1551700964975714437/browser-'+phase+'.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out));
}finally{await browser.close();}
