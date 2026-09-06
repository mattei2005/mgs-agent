import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import * as workspace from '../workspace.mjs';
const source=fs.readFileSync(new URL('../public/app.js',import.meta.url),'utf8').split("document.addEventListener('click'")[0];
const domain=JSON.parse(fs.readFileSync(new URL('../private/domain.json',import.meta.url)));
const model=JSON.parse(fs.readFileSync(new URL('../private/ui-model.json',import.meta.url)));
domain.expenses=[{id:'TEST-company',category:'company',label:'TEST expense',usd:-10,brl:-50,status:'A conferir'},{id:'TEST-personnel',category:'personnel',label:'TEST payroll',usd:-20,brl:-100,status:'Conferido',checked_on:'2026-09-08'}];
const fixture={domain,model,fx:5,additions:[],rates:workspace.rates.map(r=>({...r,value:r.type==='invalid'?'0.01':'1.25',status:'provisional'}))};
function ui(){const ctx=vm.createContext({Intl,console});vm.runInContext(source,ctx);ctx.fixture=structuredClone(fixture);vm.runInContext('data=fixture',ctx);return expr=>vm.runInContext(expr,ctx);}
test('country details default closed with native accessible summary',()=>{const run=ui();run("selectedSite='Eggbev'");const html=run('movement()');assert.match(html,/<details class="country-block"/);assert.doesNotMatch(html,/<details[^>]*\sopen/);assert.match(html,/<summary class="country-heading"/);});
test('removed notice absent from delivered HTML',()=>{assert.doesNotMatch(fs.readFileSync(new URL('../public/index.html',import.meta.url),'utf8'),/Alterações ficam na dash\. A planilha não é modificada\./);});
test('overview contains readonly expenses and estimated FX/invalids, no edit controls',()=>{const run=ui();const html=run('overview()');assert.match(html,/data-summary-expenses="company"/);assert.match(html,/data-summary-expenses="personnel"/);assert.match(html,/Cotações e inválidos/);assert.match(html,/Estimado/);assert.doesNotMatch(html,/data-expense=|data-rate=|data-archive=|id="addExpense"/);for(const e of fixture.domain.expenses.filter(e=>e.label&&!e.archived))assert.ok(html.includes(run(`esc(${JSON.stringify(e.label)})`)),e.id);});
test('conference date is strict, required only when checked; old payment statuses are not confirmation',()=>{assert.equal(typeof workspace.validateExpenseReview,'function');const valid=workspace.validateExpenseReview;assert.deepEqual(valid('Conferido','2026-09-08'),{status:'Conferido',checked_on:'2026-09-08'});assert.deepEqual(valid('a conferir','2026-09-08'),{status:'A conferir',checked_on:null});for(const d of ['',null,'2026-02-30','2026-2-03','no-date'])assert.throws(()=>valid('Conferido',d));for(const s of ['Pendente','Pago','Agendado','other'])assert.throws(()=>valid(s,null));});
