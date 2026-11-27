import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import * as workspace from '../workspace.mjs';
const source=fs.readFileSync(new URL('../public/financial-summary.js',import.meta.url),'utf8')+'\n'+fs.readFileSync(new URL('../public/app.js',import.meta.url),'utf8').split("document.addEventListener('click'")[0];
const domain=JSON.parse(fs.readFileSync(new URL('../private/domain.json',import.meta.url)));
const model=JSON.parse(fs.readFileSync(new URL('../private/ui-model.json',import.meta.url)));
domain.expenses=[{id:'TEST-company',category:'company',label:'TEST expense',usd:-10,brl:-50,status:'A conferir'},{id:'TEST-archived',category:'company',label:'SMS Funnel — pagamentos/recargas',usd:0,brl:0,archived:true,archived_usd:-20,archived_brl:-100,reclassification:'direct_monthly_cost',recognized_brl:'105.50',status:'Conferido',checked_on:'2026-09-30'},{id:'TEST-personnel',category:'personnel',label:'TEST payroll',usd:-20,brl:-100,status:'Conferido',checked_on:'2026-09-08'}];
const fixture={domain,model,period:{id:"2026-08",days:31},fx:5,additions:[],rates:workspace.rates.map(r=>({...r,value:r.type==='invalid'?'0.01':'1.25',status:'provisional'}))};
function salaryEditorFixture(id,period='2026-11',extra={}){
 const row={id,category:'personnel',label:'TEST fixed salary',mode:'BRL',edit_currency:'BRL',edit_amount:'3000.01',activity:'ATIVO',status:'A conferir',...extra};
 const nodes={};let form,submit,saved;
 const ctx=vm.createContext({Intl,console,document:{querySelector:s=>nodes[s]??(nodes[s]={value:''})},window:{MGSDisplayCurrency:{input:(v,c,f)=>String(Number(v)/Number(f)),restore:(v,o,c,f)=>String(Number(v)*Number(f))}}});
 vm.runInContext(source,ctx);ctx.fixture={...structuredClone(fixture),fx:5,period:{id:period,days:30},domain:{...structuredClone(domain),expenses:[row]}};
 ctx.capture=(title,html,fn)=>{form=html;submit=fn;};ctx.captureSave=async(k,b)=>{saved=b;};
 vm.runInContext(`data=fixture;currentPeriod=${JSON.stringify(period)};view='personnel';openEditor=capture;save=captureSave;expenseEditor(${JSON.stringify(id)})`,ctx);
 return {form,ctx,nodes,submit:async(amount='3000,01')=>{nodes['#expenseLabel']={value:row.label};nodes['#expenseCurrency']={value:'BRL'};nodes['#expenseAmount']={value:amount};nodes['#employeeActivity']={value:row.activity};nodes['#expenseStatus']={value:'A conferir'};await submit();return JSON.parse(JSON.stringify(saved));}};
}
test('five fixed salary editors use original BRL from November, not equivalent USD',async()=>{
 for(const id of ['personnel|155','personnel|156','personnel|157','personnel|158','personnel|159']){
  const f=salaryEditorFixture(id);assert.match(f.form,/Salário fixo mensal — R\$/);assert.match(f.form,/id="expenseAmount"[^>]*value="3000,01"/);assert.match(f.form,/id="expenseCurrency" value="BRL"/);assert.doesNotMatch(f.form,/Valor equivalente em USD|<select id="expenseCurrency"/);
  const original=await f.submit();assert.equal(original.currency,'BRL');assert.equal(original.amount,'3000.01');assert.equal(original.target,id);
  const changed=await f.submit('3.123,45');assert.equal(changed.amount,'3123.45');assert.equal(changed.currency,'BRL');
 }
});
test('fixed salary editor keeps inactive salary, native cents and month boundaries',()=>{
 const inactive=salaryEditorFixture('personnel|155','2026-11',{activity:'INATIVO',brl:'0',usd:'0',edit_amount:'0.01'});assert.match(inactive.form,/value="0,01"/);assert.match(inactive.form,/INATIVO/);
 const historical=salaryEditorFixture('personnel|155','2026-10');assert.doesNotMatch(historical.form,/Salário fixo mensal — R\$/);assert.match(historical.form,/Moeda da cobrança/);
 const future=salaryEditorFixture('personnel|155','2026-12');assert.match(future.form,/Salário fixo mensal — R\$/);
 const unrelated=salaryEditorFixture('TEST-other');assert.match(unrelated.form,/Valor equivalente em USD/);
 const commission=salaryEditorFixture('personnel|153','2026-11',{mode:'COMMISSION_FLOOR',manager:'kelly'});assert.match(commission.form,/Remuneração calculada automaticamente/);assert.doesNotMatch(commission.form,/id="expenseAmount"|Salário fixo mensal/);
 const mismatch=salaryEditorFixture('personnel|155','2026-11',{edit_currency:'USD'});assert.doesNotMatch(mismatch.form,/Salário fixo mensal/);
});
function ui(){const ctx=vm.createContext({Intl,console});vm.runInContext(source,ctx);ctx.fixture=structuredClone(fixture);vm.runInContext('data=fixture',ctx);return expr=>vm.runInContext(expr,ctx);}
test('country details default closed with native accessible summary',()=>{const run=ui();run("selectedSite='Eggbev'");const html=run('movement()');assert.match(html,/<details class="country-block"/);assert.doesNotMatch(html,/<details[^>]*\sopen/);assert.match(html,/<summary class="country-heading"/);});
test('removed notice absent from delivered HTML',()=>{assert.doesNotMatch(fs.readFileSync(new URL('../public/index.html',import.meta.url),'utf8'),/Alterações ficam na dash\. A planilha não é modificada\./);});
test('overview contains readonly expenses and estimated FX/invalids, no edit controls',()=>{const run=ui();const html=run('overview()');assert.match(html,/data-summary-expenses="company"/);assert.match(html,/data-summary-expenses="personnel"/);assert.match(html,/Cotações e inválidos/);assert.match(html,/Estimado/);assert.doesNotMatch(html,/data-expense=|data-rate=|data-archive=|id="addExpense"/);for(const e of fixture.domain.expenses.filter(e=>e.label&&!e.archived))assert.ok(html.includes(run(`esc(${JSON.stringify(e.label)})`)),e.id);});
test('archived reclassified expenses remain visible without entering the active balance',()=>{const run=ui();const html=run("expenseView('company')");assert.match(html,/Arquivadas \/ reclassificadas/);assert.match(html,/SMS Funnel/);assert.match(html,/Arquivada — não participa/);assert.doesNotMatch(html,/data-restore="TEST-archived"/);assert.match(html,/Reclassificada/);assert.match(html,/R\$\s*100,00/);assert.match(html,/R\$\s*105,50/);});
test('October company expenses expose prepaid credit without mixing it into active expenses',()=>{const run=ui();run("data.period={id:'2026-10',days:31};data.additions=[{kind:'prepaid_credit',date:'2026-10-01',provider:'SMS Funnel',amount:'68000.00'}]");const html=run("expenseView('company')");assert.match(html,/data-prepaid-credits/);assert.match(html,/Créditos pré-pagos SMS Funnel/);assert.match(html,/R\$\s*68\.000,00/);assert.match(html,/Não reduzem o resultado/);assert.match(html,/id="addPrepaid"/);});

test('conference date is strict, required only when checked; old payment statuses are not confirmation',()=>{assert.equal(typeof workspace.validateExpenseReview,'function');const valid=workspace.validateExpenseReview;assert.deepEqual(valid('Conferido','2026-09-08'),{status:'Conferido',checked_on:'2026-09-08'});assert.deepEqual(valid('a conferir','2026-09-08'),{status:'A conferir',checked_on:null});for(const d of ['',null,'2026-02-30','2026-2-03','no-date'])assert.throws(()=>valid('Conferido',d));for(const s of ['Pendente','Pago','Agendado','other'])assert.throws(()=>valid(s,null));});
