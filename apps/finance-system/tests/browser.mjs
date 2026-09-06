import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {openDatabase,root} from '../storage.mjs';
import {createApp} from '../server.mjs';
const db=await openDatabase();const app=await createApp(db);const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
const browser=await chromium.launch({headless:true,executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));const views=[];
try{
 await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('.cards');assert.match(await page.locator('.cards').innerText(),/90\.840,88/);
 for(const view of ['overview','cash','portfolio','daily','managers','expenses','inputs','reconciliation','audit']){
  await page.locator(`[data-view="${view}"]`).click();await page.waitForFunction(()=>document.querySelector('#content .panel')!==null);await page.waitForTimeout(150);
  const text=await page.locator('#content').innerText();assert.ok(text.length>100,view+' empty');views.push({view,title:await page.locator('#title').innerText(),table_rows:await page.locator('#content tbody tr').count()});
 }
 const domain=(await db.query("SELECT result->'domain' AS d FROM scenarios WHERE id='baseline'")).rows[0].d;const expectedEggbev=new Set(domain.facts.filter(x=>x.site.toLowerCase().includes('eggbev')).map(x=>x.site+'|'+x.country)).size;
 await page.locator('[data-view="portfolio"]').click();await page.locator('#localSearch').fill('Eggbev');assert.equal(await page.locator('#content tbody tr:visible').count(),expectedEggbev);
 await page.locator('#create').click();await page.locator('#scenarioName').fill('Homologação visual');await page.locator('#newScenarioForm button[type=submit]').click();await page.waitForFunction(()=>document.querySelector('#state').textContent.includes('editável'));
 const id=await page.locator('#scenario').inputValue();assert.notEqual(id,'baseline');
 await page.locator('[data-view="inputs"]').click();await page.waitForSelector('#sourceSearch');await page.locator('#sourceSearch').fill('Rev-share geral');await page.locator('#sourceApply').click();await page.waitForSelector('.edit');await page.locator('.edit').first().click();await page.locator('#editValue').fill('0.11');await page.locator('#editForm button[type=submit]').click();await page.waitForFunction(()=>document.querySelector('#state').textContent.includes('revisão 1'),null,{timeout:120000});
 const event=(await db.query('SELECT action FROM audit_events WHERE scenario_id=$1 ORDER BY id DESC LIMIT 1',[id])).rows[0];assert.equal(event.action,'INPUT_CHANGED');
 await page.locator('#scenario').selectOption('baseline');await page.waitForFunction(()=>document.querySelector('#state').textContent.includes('Referência'));await page.locator('[data-view="overview"]').click();assert.match(await page.locator('.cards').innerText(),/90\.840,88/);
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(100);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(root,'private','browser-evidence.json'),JSON.stringify({pass:true,views,js_errors:errors,mobile_horizontal_overflow:false,scenario_created:id,real_input_edit:true,baseline_unchanged:true},null,2));console.log(JSON.stringify({pass:true,views:views.length,js_errors:errors.length,scenario:id}));
}finally{await browser.close();await new Promise(r=>server.close(r));await db.close();}
