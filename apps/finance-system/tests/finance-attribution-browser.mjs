import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {revenueAttributionDocument} from '../accounts.mjs';

const phase=process.argv[2]||'stage';
assert.ok(['stage','production'].includes(phase));
const root=new URL('../',import.meta.url).pathname.replace(/\/$/,'');
const evidence=root+'/private/gam-sequential-1548113083774541935';
const origin='https://dash.mgsdigitalcorp.com';
const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
const credentials=JSON.parse(Buffer.concat(chunks).toString('utf8'));
let browser;
try{
 browser=await chromium.launch({executablePath:'/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({locale:'pt-BR'}),page=await context.newPage(),errors=[],stagedAttribution=phase==='stage'?await revenueAttributionDocument():null;page.on('pageerror',error=>errors.push(error.message));
 if(phase==='stage'){
  for(const file of ['app.js','navigation.js','operations.js'])await context.route(origin+'/'+file,route=>route.fulfill({path:root+'/public/'+file,contentType:'application/javascript'}));
  await context.route(origin+'/api/ad-accounts?*',async route=>{const response=await route.fetch(),body=await response.json();await route.fulfill({response,json:{...body,revenue_attribution:stagedAttribution}});});
 }
 await page.goto(origin+'/login');await page.locator('#username').fill(credentials.username);await page.locator('#password').fill(credentials.password);await page.locator('button[type=submit]').click();await page.waitForSelector('.cards');
 const get=async path=>{const response=await context.request.get(origin+path);assert.equal(response.status(),200,path);const body=await response.json();return stagedAttribution&&path.startsWith('/api/ad-accounts')?{...body,revenue_attribution:stagedAttribution}:body;};
 const periods=[];
 for(const year of [2026,2027])for(let month=1;month<=12;month++){const period=year+'-'+String(month).padStart(2,'0');if(period<'2026-09'||period>'2027-12')continue;const [workspace,accounts]=await Promise.all([get('/api/workspace?period='+period),get('/api/ad-accounts?period='+period)]);const catalog=new Set(workspace.sites.map(x=>x.name)),facts=new Set(workspace.domain.facts.map(x=>x.site));assert.deepEqual([...facts].sort(),[...catalog].sort(),period+' daily domains differ from catalog');assert.equal(accounts.revenue_attribution.authority,'1548113083774541935');periods.push({period,sites:catalog.size,aligned:true});}
 for(const period of ['2026-09','2027-12']){await page.goto(origin+'/?view=accounts&period='+period);await page.waitForSelector('[data-revenue-attribution]');const text=await page.locator('[data-revenue-attribution]').innerText();for(const value of ['Atribuição de receita por gestor','g001-d','g001-s','openzed.com','fincgriffin.com','creditoparaveiculo.com','yolokfx.com','autolendpro.comd'])assert.ok(text.includes(value),value);assert.ok(text.includes('Também: Ícaro'));}
 await page.goto(origin+'/?view=accounts&period=2026-08');await page.waitForSelector('[data-account-table]');assert.equal(await page.locator('[data-revenue-attribution]').count(),0);
 await page.setViewportSize({width:390,height:900});await page.goto(origin+'/?view=accounts&period=2026-09');await page.waitForSelector('[data-revenue-attribution]');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
 const navPage=await context.newPage();await navPage.setContent('<aside class="sidebar"></aside><button id="logout">Sair</button>');await navPage.addScriptTag({path:root+'/public/navigation.js'});await navPage.evaluate(()=>window.MGSNavigation.mount('partner','overview',false,{username:'geizian',display_name:'Geizian'}));const top=await navPage.locator('#nav > a.nav-item').allInnerTexts(),bottom=await navPage.locator('.nav-bottom > a.nav-item').allInnerTexts(),manager=await navPage.locator('#managerToggle').innerText();assert.deepEqual(top,['Dashboard','Relatório Diário']);assert.deepEqual(bottom,['Despesas Gerais','Despesas Funcionários','Câmbio e Inválidos','Pagamentos']);assert.ok(manager.includes('Gestores'));for(const forbidden of ['Cadastro de Domínios','Contas de Anúncio','Histórico de Atividades','Aprovações','Usuários'])assert.ok(!(top.concat(bottom).join('|')).includes(forbidden));
 assert.deepEqual(errors,[]);
 const output={pass:true,phase,periods:periods.length,site_lists_aligned:periods.every(x=>x.aligned),attribution_periods:['2026-09','2027-12'],partner_menu:['Dashboard','Relatório Diário','Gestores',...bottom],mobile_overflow:false,js_errors:errors};await fs.writeFile(evidence+'/'+phase+'-browser.json',JSON.stringify(output,null,2)+'\n');console.log(JSON.stringify(output));
}catch(error){console.error(JSON.stringify({pass:false,phase,error:error.stack?.slice(0,3000)||error.message}));process.exitCode=1;}finally{await browser?.close();}
